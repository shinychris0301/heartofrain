"""Fail-closed worker-version registry groundwork, not wired to live replay.

Callers must persist bindings in the same transaction as attempt reservation and
must migrate legacy attempts using independently verified operator provenance.
This module does neither and MUST NOT be used as evidence of a safe cutover.
"""
from dataclasses import dataclass
from types import MappingProxyType

from .replay_contract import ApprovedWorker, ReplayError, _hash, encode_job


@dataclass(frozen=True, slots=True)
class AttemptVersion:
    approval_sha256: str
    pins_sha256: str
    level: int
    level_sha256: str
    initial_moves: int


class WorkerRegistry:
    """Trusted configuration only: players cannot supply workers or versions."""
    def __init__(self, workers, active_approval_sha256):
        if not _hash(active_approval_sha256):
            raise ReplayError('invalid_active_worker')
        values = {}
        for worker in workers:
            if not isinstance(worker, ApprovedWorker) or not worker.enabled or worker.timeout > 90:
                raise ReplayError('replay_worker_not_approved')
            approval = getattr(worker, 'approval_sha256', None)
            if not _hash(approval) or approval in values:
                raise ReplayError('invalid_worker_registry')
            _, pins, pins_sha = worker._verify_bundle()
            if not _hash(pins_sha) or type(pins) is not dict or type(pins.get('levels')) is not list or len(pins['levels']) != 50:
                raise ReplayError('invalid_worker_pins')
            rows = []
            for number, pin in enumerate(pins['levels'], 1):
                if (type(pin) is not dict or type(pin.get('level')) is not int or pin['level'] != number
                        or not _hash(pin.get('sha256')) or type(pin.get('moves')) is not int or not 1 <= pin['moves'] <= 1000):
                    raise ReplayError('invalid_worker_pins')
                rows.append((pin['sha256'], pin['moves']))
            values[approval] = (worker, pins_sha, tuple(rows))
        if active_approval_sha256 not in values:
            raise ReplayError('active_worker_missing')
        self._workers = MappingProxyType(values)
        self._active = active_approval_sha256

    def reserve_binding(self, level, catalog_hash, catalog_moves):
        """Return binding for server's active catalog; caller must persist atomically."""
        binding = self.reserve_binding_metadata(level, catalog_hash, catalog_moves)
        self.resolve(binding)
        return binding

    def reserve_binding_metadata(self, level, catalog_hash, catalog_moves):
        """Compare already verified registry metadata; performs no file I/O."""
        if type(level) is not int or not 1 <= level <= 50:
            raise ReplayError('invalid_worker_level')
        worker, pins_sha, rows = self._workers[self._active]
        expected_hash, expected_moves = rows[level - 1]
        if catalog_hash != expected_hash or type(catalog_moves) is not int or catalog_moves != expected_moves:
            raise ReplayError('catalog_worker_mismatch')
        binding = AttemptVersion(self._active, pins_sha, level, expected_hash, expected_moves)
        self.resolve_metadata(binding)
        return binding

    def resolve_metadata(self, binding):
        """Fence an immutable binding without file I/O inside a DB transaction."""
        if type(binding) is not AttemptVersion or not _hash(binding.approval_sha256) or not _hash(binding.pins_sha256) or not _hash(binding.level_sha256) or type(binding.level) is not int or not 1 <= binding.level <= 50 or type(binding.initial_moves) is not int or not 1 <= binding.initial_moves <= 1000:
            raise ReplayError('invalid_attempt_version')
        entry = self._workers.get(binding.approval_sha256)
        if entry is None:
            raise ReplayError('attempt_worker_unavailable')
        worker, pins_sha, rows = entry
        if not worker.enabled or worker.timeout > 90 or worker.approval_sha256 != binding.approval_sha256:
            raise ReplayError('attempt_worker_unavailable')
        if pins_sha != binding.pins_sha256 or rows[binding.level - 1] != (binding.level_sha256, binding.initial_moves):
            raise ReplayError('attempt_version_mismatch')
        return worker

    def resolve(self, binding):
        """Reverify a complete approved bundle outside any DB transaction."""
        worker = self.resolve_metadata(binding)
        _, pins_sha, rows = self._workers[binding.approval_sha256]
        _, pins, verified_sha = worker._verify_bundle()
        pin = pins['levels'][binding.level - 1]
        if (verified_sha != pins_sha or verified_sha != binding.pins_sha256
                or rows[binding.level - 1] != (binding.level_sha256, binding.initial_moves)
                or pin['level'] != binding.level or pin['sha256'] != binding.level_sha256
                or pin['moves'] != binding.initial_moves):
            raise ReplayError('attempt_version_mismatch')
        return worker

    def verify_all(self):
        """Revalidate all configured versions outside any DB transaction."""
        for approval, (_, pins_sha, rows) in self._workers.items():
            digest, moves = rows[0]
            self.resolve(AttemptVersion(approval, pins_sha, 1, digest, moves))

    def run(self, binding, job):
        """Select a worker from the saved binding, never from client job fields."""
        worker = self.resolve(binding)
        encode_job(job)
        if (job['pinsSHA256'] != binding.pins_sha256 or job['levelSHA256'] != binding.level_sha256
                or job['level'] != binding.level or job['initialMoves'] != binding.initial_moves):
            raise ReplayError('attempt_version_mismatch')
        return worker.run(job)
