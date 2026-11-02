"""Explicit, lock-held staging ASGI construction for schema16.

No listener, process, deployment, provider activation or production mode is
started here. A caller must keep the context open until the ASGI server stops.
Historic unbound attempts cannot be migrated by this module.
"""
from contextlib import contextmanager
from functools import wraps
import asyncio
import concurrent.futures
import hashlib
import inspect
from pathlib import Path
import threading

from . import staging105 as staging
from .staging_empty_versioned_upgrade117 import PREPARED
from .staging_versioned_preflight117 import verify_prepared_authority
from .wallet_schemas import LevelCatalog
from .service import ServiceError

_SECRET = object()


class _Permit:
    def __init__(self, secret, manifest, registry, catalog):
        if secret is not _SECRET:
            raise RuntimeError('Owned staging permit required')
        self.manifest, self.registry, self.catalog = manifest, registry, catalog
        self._open = True
        self._inflight = 0
        self._condition = threading.Condition()

    def validate(self, database_path):
        with self._condition:
            if not self._open:
                raise RuntimeError('Owned staging permit closed')
        expected = staging.owned_database(self.manifest, allowed_states=(PREPARED,))
        if database_path is None or Path(database_path).resolve() != expected.resolve():
            raise RuntimeError('Owned staging authority mismatch')
        staging._plain(expected)

    def enter(self):
        with self._condition:
            if not self._open:
                return False
            self._inflight += 1
            return True

    def leave(self):
        with self._condition:
            self._inflight -= 1
            if self._inflight == 0:
                self._condition.notify_all()

    def close(self):
        # Refuse new requests and retain the runtime lock until all existing
        # requests finish; never release ownership while a commit is in flight.
        with self._condition:
            self._open = False
            while self._inflight:
                self._condition.wait()


def fence_routes(app, permit, notifications, reviewed_notifications=()):
    """Track actual FastAPI worker calls even when the ASGI task is cancelled."""
    from fastapi.routing import APIRoute
    from fastapi.security import HTTPBearer
    visited = set()

    def guarded(call):
        @wraps(call)
        def run(*args, **kwargs):
            if not permit.enter():
                raise ServiceError(503, 'staging_runtime_closed')
            try:
                return call(*args, **kwargs)
            finally:
                permit.leave()
        return run

    def visit(dependant, allow_notification=False):
        if id(dependant) in visited:
            return
        visited.add(id(dependant))
        for child in dependant.dependencies:
            visit(child)
        call = dependant.call
        if inspect.isfunction(call) and not inspect.iscoroutinefunction(call):
            dependant.call = guarded(call)
        elif inspect.isfunction(call) and not allow_notification:
            # New async endpoints need an explicit audit for detached work.
            raise RuntimeError('Unaudited async staging endpoint')
        elif not inspect.isfunction(call) and type(call) is not HTTPBearer:
            # Callable dependencies can also dispatch work; do not silently
            # admit a new object type that has not been reviewed and fenced.
            raise RuntimeError('Unaudited callable staging dependency')

    # These two reviewed async notification endpoints call this synchronous
    # function through a threadpool. Fence it independently of cancellation.
    notifications.receive = guarded(notifications.receive)
    allowed = dict(reviewed_notifications)
    for route in app.routes:
        if isinstance(route, APIRoute):
            allow = allowed.get(route.path) is route.dependant.call
            visit(route.dependant, allow_notification=allow)


@contextmanager
def _open_versioned_application(manifest, registry, catalog_path, catalog_sha256, *, clock=None):
    """Yield an ASGI app while owning the runtime lock; never bind a socket."""
    m = staging.read_manifest(manifest)
    permit = None
    with staging._lock(m, staging.RUNTIME_LOCK, allowed_states=(PREPARED,)):
        with staging.root_lock(m, allowed_states=(PREPARED,)):
            if m.replay.enabled:
                raise staging.StagingError('versioned_runtime_legacy_worker_configuration_conflict')
            verify_prepared_authority(m, registry, catalog_path, catalog_sha256, _locks_held=True)
            path = staging._private_path(Path(catalog_path))
            staging._plain(path)
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != catalog_sha256:
                raise staging.StagingError('versioned_preflight_catalog_mismatch')
            catalog = LevelCatalog.model_validate_json(raw)
            permit = _Permit(_SECRET, m, registry, catalog)
            from .api import create_app
            from .vk_provider import VkConfiguration
            from .rustore_provider import UnavailablePurchaseProvider
            try:
                app = create_app(database_path=m.data_directory / staging.DATABASE, config_path=staging.CONFIG,
                                 clock=clock, commerce_config_path=m.data_directory / staging.COMMERCE,
                                 commerce_provider=UnavailablePurchaseProvider(), identity_enabled=True,
                                 social_enabled=True, notifications_enabled=False, replay_enabled=True,
                                 ads_config_path=m.data_directory / staging.ADS,
                                 vk_configuration=VkConfiguration(m.vk.enabled, m.vk.client_id, m.vk.redirect_uri),
                                 _versioned_staging_permit117=permit)
            except BaseException:
                permit.close()
                raise
        try:
            yield app
        finally:
            permit.close()


class _ApplicationContext:
    """Support sync callers and async shutdown without blocking an event loop."""
    def __init__(self, inner):
        self._inner = inner
        self._exit_lock = threading.Lock()
        self.closed = threading.Event()
        self.close_error = None

    def _enter(self):
        return self._inner.__enter__()

    def __enter__(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self._enter()
        raise RuntimeError('Use async with for a running event loop')

    def _exit(self, exc_type, exc, traceback):
        with self._exit_lock:
            try:
                return self._inner.__exit__(exc_type, exc, traceback)
            except BaseException as error:
                self.close_error = error
                raise
            finally:
                self.closed.set()

    def __exit__(self, exc_type, exc, traceback):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self._exit(exc_type, exc, traceback)
        # A context entered on a different thread may be closed from an event
        # loop. Return control to that loop while a non-daemon thread retains
        # ownership until all actual synchronous workers have drained.
        def finish():
            try:
                self._exit(None, None, None)
            except BaseException:
                pass  # exposed through close_error and closed, never logged
        threading.Thread(target=finish, name='hotr-staging-drain117', daemon=False).start()
        return False

    async def __aenter__(self):
        future = self._thread_call(self._enter)
        try:
            # Shield the actual thread result: cancellation of the calling
            # task must not lose the ability to close a late successful entry.
            return await asyncio.shield(asyncio.wrap_future(future))
        except asyncio.CancelledError:
            def cleanup():
                try:
                    future.result()
                except BaseException as error:
                    self.close_error = error
                    self.closed.set()
                    return
                try:
                    self._exit(None, None, None)
                except BaseException:
                    pass  # reported via close_error and closed
            threading.Thread(target=cleanup, name='hotr-staging-entry-cleanup117', daemon=False).start()
            raise
        except BaseException as error:
            self.close_error = error
            self.closed.set()
            raise

    async def __aexit__(self, exc_type, exc, traceback):
        future = self._thread_call(self._exit, exc_type, exc, traceback)
        return await asyncio.shield(asyncio.wrap_future(future))

    @staticmethod
    def _thread_call(call, *args):
        future = concurrent.futures.Future()
        def run():
            try:
                future.set_result(call(*args))
            except BaseException as error:
                future.set_exception(error)
        # Non-daemon ownership outlives a cancelled task and its event loop.
        threading.Thread(target=run, name='hotr-staging-context117', daemon=False).start()
        return future


def open_versioned_application(manifest, registry, catalog_path, catalog_sha256, *, clock=None):
    """Return a sync/async lock-held ASGI context; never bind a socket."""
    return _ApplicationContext(_open_versioned_application(manifest, registry, catalog_path, catalog_sha256, clock=clock))
