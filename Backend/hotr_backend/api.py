import ipaddress
import os
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from .schemas import Command, CupClaimRequest, EventBatch, GiftRequest, MilestoneRequest, VerifiedClear
from .service import Authority, ServiceError
from .storage import Database
from .commerce import Commerce
from .commerce_schemas import CreateCommerceOrder, ReconcileCommerceOrder
from .wallet import Wallet
from .wallet_schemas import ReserveAttempt, SettleAttempt, SpendTool, WalletCommand
from .identity import ManagedIdentity
from .identity_schemas import ChallengeRequest, GuestRequest, SessionRequest, RecoverRequest, LogoutRequest, DeletionRequest
from .notifications import NotificationInbox, file_key_source
from .notification_worker import ReconciliationWorker
from .friends import Friends
from .social_schemas import ProfileUpdate, ProfileNameUpdate, ProfileConsentUpdate, FriendTarget, FriendResponse
from .messaging import Messaging
from .messaging_schemas import CreateTeam, TeamTarget, TeamLeave, SendMessage, ReadMessages, ReportMessage, ModerateMessage
from .records import Records
from .regions import Regions, RegionUpdate
from .provider_identity import ProviderIdentity, register_provider_routes
from .provider_signin102 import ProviderSignin102, register_signin_routes102
from .ugc_moderation import UgcModeration
from .ugc_schemas import UgcReport, UgcModerate
from .replay_contract import ApprovedWorker
from .replay_service import ReplayBroker
from .replay_schemas import VerifyReplay, ReplayTool, ReplayContinue, ResumeReplay
from .social_operations import SocialOperations
from .newads import RewardedAds
from .newads_schemas import ReserveRewardedAd, RewardedAdCommand

from .http_ingress import BoundedBody, MAX_BODY
from .readiness import database_write_ready
from .runtime136 import LOG, Metrics, RequestGuard, SHED_RETRY_SECONDS, ServiceRuntime


from .team_life110 import TeamLife110, TeamLifeRules110
from .team_mail111 import TeamMail111
from .team_invites112 import TeamInvites112, TeamInvitePolicy112


def create_app(database_path=None, config_path=None, clock=None, commerce_provider=None, commerce_config_path=None,
               identity_enabled=None, notifications_enabled=None, notification_key_source=None,
               notification_allowed_networks=None, social_enabled=None, replay_enabled=None, replay_worker=None,
               ads_config_path=None, ads_verifier=None, vk_configuration=None, vk_provider=None,
               trusted_client_header=None, service_runtime=False,
               _versioned_staging_permit117=None, _production_permit122=None, _staging_sdk_permit126=None):
    permit = _versioned_staging_permit117
    production_permit = _production_permit122
    sdk_staging_permit = _staging_sdk_permit126
    if production_permit is not None:
        from .production_runtime122 import _ProductionPermit
        if type(production_permit) is not _ProductionPermit or permit is not None or sdk_staging_permit is not None:
            raise RuntimeError('Explicit owned production permit required')
        production_permit.validate(database_path)
        m = production_permit.manifest
        sdk_mode = m.verification_mode == 'sdk_client_reported'
        if (identity_enabled is not True or social_enabled is not True or notifications_enabled is not (not sdk_mode)
                or replay_enabled is not True or replay_worker is None
                or (not sdk_mode and commerce_provider is None)
                or config_path is None or Path(config_path).resolve() != m.config_directory.resolve()
                or commerce_config_path is None or Path(commerce_config_path).resolve() != m.commerce_config.resolve()):
            raise RuntimeError('Production service bindings required')
    if permit is not None:
        from .staging_versioned_runtime117 import _Permit
        if type(permit) is not _Permit or replay_enabled is not True or replay_worker is not None:
            raise RuntimeError('Explicit owned staging replay permit required')
        permit.validate(database_path)
    if sdk_staging_permit is not None:
        from .staging_sdk126 import _Permit as SdkStagingPermit, CATALOG as SDK_CATALOG126
        from . import staging105 as staging126
        if type(sdk_staging_permit) is not SdkStagingPermit or permit is not None or production_permit is not None:
            raise RuntimeError('Explicit owned SDK staging126 permit required')
        sdk_staging_permit.validate(database_path)
        sm = sdk_staging_permit.manifest
        if (identity_enabled is not True or social_enabled is not True or notifications_enabled is not False
                or replay_enabled is not sm.replay.enabled
                or bool(replay_worker is not None) != sm.replay.enabled
                or config_path is None or Path(config_path).resolve() != staging126.CONFIG.resolve()
                or commerce_config_path is None
                or Path(commerce_config_path).resolve() != sm.data_directory / SDK_CATALOG126
                or ads_config_path is None or Path(ads_config_path).resolve() != sm.data_directory / staging126.ADS):
            raise RuntimeError('SDK staging126 service bindings required')
    configured_mode = ('production' if production_permit is not None else 'staging'
                       if sdk_staging_permit is not None else os.getenv('HOTR_BACKEND_MODE', 'local'))
    if production_permit is None and configured_mode not in ('local', 'staging'):
        raise RuntimeError('Production activation requires hosting, identity and recovery integration; use local or staging')
    mode = 'production' if production_permit is not None else 'staging' if permit is not None else configured_mode
    root = Path(__file__).resolve().parents[1]
    data = Path(os.getenv('HOTR_BACKEND_DATA_DIR', str(root / '.local')))
    life_rules = TeamLifeRules110.model_validate_json((Path(config_path or root / 'config') / 'team_help.json').read_bytes())
    invite_policy = TeamInvitePolicy112.model_validate_json((Path(config_path or root / 'config') / 'team_invites.json').read_bytes())
    from .commerce_schemas import CommerceConfig
    selected_commerce = Path(commerce_config_path or root / 'config/commerce.json')
    commerce_settings = CommerceConfig.model_validate_json(selected_commerce.read_text('utf-8-sig'))
    sdk_mode = commerce_settings.verificationMode == 'sdk_client_reported'
    if sdk_staging_permit is not None and (
            not sdk_mode or commerce_settings.sandbox is not True
            or commerce_settings.appId != sdk_staging_permit.policy['appId']):
        raise RuntimeError('SDK staging126 catalogue binding required')
    if sdk_mode and permit is not None:
        raise RuntimeError('SDK125 is separate from versioned staging117')
    # An owned SDK launcher has just checked the schema. Whole-file checks belong to deploy and restore.
    authority = Authority(Database(database_path or data / 'authority.sqlite3',
                          _versioned_staging117=permit is not None, _sdk_commerce125=sdk_mode,
                          _open_integrity_check=sdk_staging_permit is None),
                          config_path or root / 'config', clock)
    if production_permit is not None:
        authority._runtime_policy122 = production_permit.policy
    wallet = Wallet(authority, config_path or root / 'config')
    if permit is not None:
        wallet.catalog = permit.catalog
    commerce = Commerce(authority, commerce_config_path or root / 'config/commerce.json', commerce_provider)
    if production_permit is not None and (
            not commerce.config.enabled or commerce.config.sandbox
            or commerce.config.verificationMode != production_permit.manifest.verification_mode
            or (not sdk_mode and not commerce.provider.configured)
            or (sdk_mode and commerce.provider.configured)):
        raise RuntimeError('Production explicit commerce verification configuration required')
    def enabled(value, name):
        if value is None:
            raw = os.getenv(name, '0')
            if raw not in ('0', '1'):
                raise RuntimeError('Invalid explicit feature configuration')
            return raw == '1'
        if type(value) is not bool:
            raise RuntimeError('Invalid explicit feature configuration')
        return value
    identity = ManagedIdentity(authority, enabled=enabled(identity_enabled, 'HOTR_MANAGED_IDENTITY_ENABLED'))
    notifications_on = enabled(notifications_enabled, 'HOTR_RUSTORE_NOTIFICATIONS_ENABLED')
    if sdk_mode and (notifications_on or notification_key_source is not None):
        raise RuntimeError('SDK client-reported mode has no provider notifications')
    if notifications_on and notification_key_source is None:
        path = os.getenv('HOTR_RUSTORE_NOTIFICATION_KEY_FILE')
        if not path:
            raise RuntimeError('Explicit server notification key reference required')
        notification_key_source = file_key_source(path)
    if notification_allowed_networks is None:
        notification_allowed_networks = tuple(v.strip() for v in os.getenv('HOTR_RUSTORE_NOTIFICATION_ALLOWED_CIDRS', '').split(',') if v.strip())
    notifications = NotificationInbox(authority, commerce, notification_key_source, notification_allowed_networks, notifications_on)
    social_on = enabled(social_enabled, 'HOTR_SOCIAL_ENABLED')
    friends = Friends(authority, enabled=social_on)
    messaging = Messaging(authority, enabled=social_on)
    team_life = TeamLife110(authority, wallet, messaging, life_rules, enabled=social_on)
    team_mail = TeamMail111(authority, wallet, messaging, enabled=social_on)
    team_invites = TeamInvites112(authority, messaging, invite_policy, enabled=social_on)
    records = Records(authority, enabled=social_on)
    regions = Regions(authority, enabled=social_on)
    provider_identity = ProviderIdentity(authority, vk_configuration, vk_provider)
    provider_signin = ProviderSignin102(identity, provider_identity)
    ugc = UgcModeration(authority, enabled=social_on)
    social_operations = SocialOperations(authority, enabled=social_on)
    replay_on = enabled(replay_enabled, 'HOTR_GAMEPLAY_REPLAY_ENABLED')
    if replay_on and replay_worker is None and permit is None:
        values = [os.getenv(name) for name in ('HOTR_REPLAY_BUNDLE', 'HOTR_REPLAY_APPROVAL_FILE', 'HOTR_REPLAY_APPROVAL_SHA256', 'HOTR_REPLAY_JOB_DIR')]
        if not all(values): raise RuntimeError('Explicit approved replay worker configuration required')
        replay_worker = ApprovedWorker(*values, enabled=True)
    bound_attempts = None
    if permit is not None:
        from .staging_versioned_replay117 import StagingBoundAttempts, StagingVersionedReplay
        bound_attempts = StagingBoundAttempts(wallet, permit.registry)
        replay = StagingVersionedReplay(bound_attempts)
    else:
        replay = ReplayBroker(authority, wallet, replay_worker, enabled=replay_on, dispatcher=service_runtime and replay_on)
    ads = RewardedAds(authority, ads_config_path or root / 'config/ads.json', ads_verifier)
    app = FastAPI(title='Heart of the Rain authority', version='1.0.0', docs_url=None, redoc_url=None)
    active_staging_permit = permit if permit is not None else sdk_staging_permit
    if active_staging_permit is not None:
        @app.middleware('http')
        async def versioned_owner_gate(request, call_next):
            if not active_staging_permit.enter():
                return JSONResponse({'error': 'staging_runtime_closed'}, status_code=503, headers={'Retry-After': str(SHED_RETRY_SECONDS)})
            try:
                return await call_next(request)
            finally:
                active_staging_permit.leave()
    if production_permit is not None:
        @app.middleware('http')
        async def production_owner_gate(request, call_next):
            if not production_permit.enter():
                return JSONResponse({'error': 'production_runtime_closed'}, status_code=503, headers={'Retry-After': str(SHED_RETRY_SECONDS)})
            try:
                return await call_next(request)
            finally:
                production_permit.leave()
        app.state.production_permit122 = production_permit
    if sdk_staging_permit is not None:
        app.state.sdk_staging_permit126 = sdk_staging_permit
    app.state.authority = authority
    app.state.commerce = commerce
    app.state.wallet = wallet
    app.state.identity = identity
    app.state.notifications = notifications
    app.state.reconciliation_worker = ReconciliationWorker(notifications, commerce)
    app.state.friends, app.state.messaging, app.state.records = friends, messaging, records
    app.state.ugc = ugc
    app.state.regions = regions
    app.state.team_life = team_life
    app.state.team_mail = team_mail
    app.state.team_invites = team_invites
    app.state.provider_identity = provider_identity
    app.state.provider_signin = provider_signin
    app.state.replay_broker = replay
    app.state.rewarded_ads = ads
    app.add_middleware(BoundedBody)
    bearer = HTTPBearer(auto_error=False)

    def actor(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        return authority.authenticate(credentials.credentials if credentials else None)

    def source(request):
        if production_permit is not None:
            return production_permit.client_address(request)
        # Uvicorn's socket peer by default. A trusted loopback proxy overwrites
        # this one header; any other peer or malformed value keeps the socket peer.
        peer = request.client.host if request.client else 'unknown-peer'
        if trusted_client_header and peer in ('127.0.0.1', '::1'):
            values = request.headers.getlist(trusted_client_header)
            if len(values) == 1:
                try:
                    address = ipaddress.ip_address(values[0])
                except ValueError:
                    return peer
                if str(address) == values[0] and not address.is_loopback and not address.is_unspecified:
                    return values[0]
        return peer

    register_provider_routes(app, provider_identity, actor, provider_signin)
    register_signin_routes102(app, provider_signin, actor, source_resolver=source)

    def verifier(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        return authority.authenticate(credentials.credentials if credentials else None, 'verifier')

    @app.middleware('http')
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    metrics = Metrics()
    app.state.metrics136 = metrics
    runtime = None
    if service_runtime:
        runtime = ServiceRuntime(authority, metrics, replay, getattr(replay_worker, 'jobs', None))
        app.state.service_runtime136 = runtime
    app.add_middleware(RequestGuard, metrics=metrics, runtime=runtime)

    @app.exception_handler(ServiceError)
    async def service_error(request, error):
        headers = {'WWW-Authenticate': 'Bearer'} if error.status == 401 else {}
        if error.status == 429:
            headers['Retry-After'] = '30'
        elif error.status == 503:
            headers['Retry-After'] = str(SHED_RETRY_SECONDS)
        return JSONResponse({'error': error.code}, status_code=error.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo arbitrary input, credentials, body or validator internals.
        return JSONResponse({'error': 'invalid_request'}, status_code=422)

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, error):
        metrics.count('storageErrors')
        LOG.warning('hotr_storage_error %s', type(error).__name__)
        return JSONResponse({'error': 'storage_unavailable'}, status_code=503, headers={'Retry-After': str(SHED_RETRY_SECONDS)})

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        metrics.count('internalErrors')
        LOG.warning('hotr_internal_error %s', type(error).__name__)
        return JSONResponse({'error': 'internal_error'}, status_code=500)

    @app.get('/healthz')
    def health():
        return {'status': 'ok', 'mode': mode, 'productionEnabled': production_permit is not None}

    @app.get('/readyz')
    def ready():
        valid = database_write_ready(authority.database)
        return JSONResponse({'status': 'ready' if valid else 'unavailable'}, status_code=200 if valid else 503)

    @app.get('/v1/time')
    def server_time(current=Depends(actor)):
        return {'serverUtc': current.now, 'day': current.now // 86400}

    @app.get('/v1/ads/rewarded/status')
    def rewarded_ad_status(utcOffsetSeconds: int | None = None, timeZoneId: str | None = Query(None, max_length=128), current=Depends(actor)):
        return ads.status(current, utcOffsetSeconds, timeZoneId)

    @app.post('/v1/ads/rewarded/reserve')
    def rewarded_ad_reserve(body: ReserveRewardedAd, current=Depends(actor)):
        return ads.reserve(current, body)

    @app.get('/v1/ads/rewarded/opportunities/{opportunity_id}')
    def rewarded_ad_opportunity(opportunity_id: str, current=Depends(actor)):
        return ads.opportunity(current, opportunity_id)

    @app.post('/v1/ads/rewarded/opportunities/{opportunity_id}/client-completion')
    def rewarded_ad_client_completion(opportunity_id: str, body: RewardedAdCommand, current=Depends(actor)):
        return ads.client_completion(current, opportunity_id, body)

    @app.post('/v1/ads/rewarded/opportunities/{opportunity_id}/claim')
    def rewarded_ad_claim(opportunity_id: str, body: RewardedAdCommand, current=Depends(actor)):
        return ads.claim(current, opportunity_id, body)

    @app.post('/v1/ads/rewarded/opportunities/{opportunity_id}/cancel')
    def rewarded_ad_cancel(opportunity_id: str, body: RewardedAdCommand, current=Depends(actor)):
        return ads.cancel(current, opportunity_id, body)

    @app.post('/v1/identity/challenges')
    def identity_challenge(body: ChallengeRequest, request: Request):
        return identity.challenge(body, source_key=source(request))

    @app.post('/v1/identity/guest')
    def identity_guest(body: GuestRequest, request: Request):
        return identity.guest(body, source_key=source(request))

    @app.post('/v1/identity/session')
    def identity_session(body: SessionRequest, request: Request):
        return identity.session(body, source_key=source(request))

    @app.post('/v1/identity/recover')
    def identity_recover(body: RecoverRequest, request: Request):
        return identity.recover(body, source_key=source(request))

    @app.post('/v1/identity/logout')
    def identity_logout(body: LogoutRequest, request: Request):
        return identity.logout(None, body, source_key=source(request))

    @app.post('/v1/account/deletion', description='Signed re-authentication and revocation; restricted financial retention remains explicit, not an all-storage erase claim.')
    def account_deletion(body: DeletionRequest, request: Request):
        return identity.deletion(None, body, source_key=source(request))

    @app.get('/v1/region')
    def player_region(current=Depends(actor)):
        return regions.mine(current)

    @app.post('/v1/region')
    def player_region_update(body: RegionUpdate, current=Depends(actor)):
        return regions.update(current, body)

    @app.get('/v1/team-leaderboards/{scope}')
    def team_leaderboard(scope: str, offset: int = Query(0, ge=0, le=10_000), limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return records.team_leaderboard(current, scope, offset, limit)

    @app.get('/v1/team-leaderboards-refresh/{scope}')
    def team_leaderboard_refresh(scope: str, offset: int = Query(0, ge=0, le=10_000), limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return records.team_leaderboard(current, scope, offset, limit, include_self=True)

    @app.get('/v1/profile')
    def social_me(current=Depends(actor)):
        return friends.me(current)

    @app.post('/v1/profile')
    def social_update(body: ProfileUpdate, current=Depends(actor)):
        return friends.update_profile(current, body)

    @app.post('/v1/profile/name')
    def social_update_name(body: ProfileNameUpdate, current=Depends(actor)):
        return friends.update_name(current, body)

    @app.post('/v1/profile/leaderboard-consent')
    def social_update_consent(body: ProfileConsentUpdate, current=Depends(actor)):
        return friends.update_consent(current, body)

    @app.get('/v1/players/{player_id}')
    def social_profile(player_id: str, current=Depends(actor)):
        return friends.profile(current, player_id)

    @app.get('/v1/friends')
    def friend_list(after: str = '', limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return friends.list(current, after, limit)

    @app.get('/v1/friends/search')
    def friend_search(q: str, after: str = '', limit: int = Query(20, ge=1, le=100), current=Depends(actor)):
        return friends.search(current, q, after, limit)

    @app.get('/v1/friends/relationship/{player_id}')
    def friend_relationship(player_id: str, current=Depends(actor)):
        return friends.relationship(current, player_id)

    @app.get('/v1/friends/requests')
    def friend_requests(after: str = '', limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return friends.requests(current, after, limit)

    @app.post('/v1/friends/request')
    def friend_request(body: FriendTarget, current=Depends(actor)):
        return friends.send(current, body)

    @app.post('/v1/friends/respond')
    def friend_respond(body: FriendResponse, current=Depends(actor)):
        return friends.respond(current, body)

    @app.post('/v1/friends/remove')
    def friend_remove(body: FriendTarget, current=Depends(actor)):
        return friends.remove(current, body)

    @app.post('/v1/blocks/add')
    def block_add(body: FriendTarget, current=Depends(actor)):
        return friends.block(current, body)

    @app.post('/v1/blocks/remove')
    def block_remove(body: FriendTarget, current=Depends(actor)):
        return friends.unblock(current, body)

    @app.get('/v1/blocks')
    def block_list(after: str = '', limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return friends.blocks(current, after, limit)

    @app.get('/v1/records')
    def records_mine(after: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return records.mine(current, after, limit)

    @app.get('/v1/leaderboards/{scope}')
    def leaderboard(scope: str, offset: int = Query(0, ge=0, le=10_000), limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return records.leaderboard(current, scope, offset, limit)

    @app.get('/v1/leaderboards-refresh/{scope}')
    def leaderboard_refresh(scope: str, offset: int = Query(0, ge=0, le=10_000), limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return records.leaderboard(current, scope, offset, limit, include_self=True)

    @app.get('/v1/teams')
    def team_list(after: str = '', limit: int = Query(50, ge=1, le=100), query: str = Query('', max_length=128), current=Depends(actor)):
        return messaging.teams(current, after, limit, query)

    @app.get('/v1/social/operations/{command_id}')
    def social_operation(command_id: str, operation: str, current=Depends(actor)):
        return social_operations.get(current, command_id, operation)

    @app.get('/v1/teams/{team_id}/life-requests')
    def team_life_requests(team_id: str, before: int | None = Query(None, ge=1), limit: int = Query(8, ge=1, le=8), messageIds: str | None = Query(None, max_length=263), current=Depends(actor)):
        return team_life.team_requests(current, team_id, before=before, limit=limit, message_ids=messageIds)

    @app.get('/v1/teams/{team_id}/invitations')
    def invite_friends(team_id: str, after: str = '', query: str = Query('', max_length=128), limit: int = Query(8, ge=1, le=8), current=Depends(actor)):
        return team_invites.friends(current, team_id, after, query, limit)

    @app.post('/v1/teams/{team_id}/invitations/{friend_id}')
    def invite_send(team_id: str, friend_id: str, body: Command, current=Depends(actor)):
        return team_invites.send(current, team_id, friend_id, body)

    @app.get('/v1/invitations/received')
    def invite_received(before: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(8, ge=1, le=8), current=Depends(actor)):
        return team_invites.received(current, before, limit)

    @app.get('/v1/invitations/{invite_id}')
    def invite_detail(invite_id: str, current=Depends(actor)):
        return team_invites.detail(current, invite_id)

    @app.post('/v1/teams/{team_id}/life-requests')
    def team_life_request(team_id: str, body: Command, current=Depends(actor)):
        return team_life.request(current, team_id, body)

    @app.post('/v1/teams/{team_id}/life-requests/{request_id}/help')
    def team_life_help(team_id: str, request_id: str, body: Command, current=Depends(actor)):
        return team_life.help(current, team_id, request_id, body)

    @app.get('/v1/life-requests/owned')
    def owned_life_requests(after: int = Query(0, ge=0), limit: int = Query(8, ge=1, le=8), current=Depends(actor)):
        return team_life.owned(current, after, limit)

    @app.post('/v1/life-requests/{request_id}/claim')
    def team_life_claim(request_id: str, body: Command, current=Depends(actor)):
        return team_life.claim(current, request_id, body)

    @app.get('/v1/teams/{team_id}/mail')
    def team_mail_list(team_id: str, before: int | None = Query(None, ge=1), limit: int = Query(8, ge=1, le=8), current=Depends(actor)):
        return team_mail.list(current, team_id, before, limit)

    @app.get('/v1/teams/{team_id}/mail/{message_id}')
    def team_mail_detail(team_id: str, message_id: str, current=Depends(actor)):
        return team_mail.detail(current, team_id, message_id)

    @app.post('/v1/teams/{team_id}/mail/{message_id}/read')
    def team_mail_read(team_id: str, message_id: str, body: Command, current=Depends(actor)):
        return team_mail.read(current, team_id, message_id, body)

    @app.post('/v1/teams/{team_id}/mail/{message_id}/claim')
    def team_mail_claim(team_id: str, message_id: str, body: Command, current=Depends(actor)):
        return team_mail.claim(current, team_id, message_id, body)

    @app.get('/v1/mail/rewards/owned')
    def mail_rewards_owned(after: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(8, ge=1, le=8), current=Depends(actor)):
        return team_mail.owned(current, after, limit)

    @app.post('/v1/mail/rewards/{message_id}/claim')
    def mail_reward_claim(message_id: str, body: Command, current=Depends(actor)):
        return team_mail.claim(current, None, message_id, body, owned=True)

    @app.post('/v1/teams')
    def team_create(body: CreateTeam, current=Depends(actor)):
        return messaging.create_team(current, body)

    @app.get('/v1/teams/{team_id}')
    def team_view(team_id: str, current=Depends(actor)):
        return messaging.team(current, team_id)

    @app.post('/v1/teams/{team_id}/join')
    def team_join(team_id: str, body: Command, current=Depends(actor)):
        return messaging.join(current, team_id, body)

    @app.post('/v1/teams/{team_id}/leave')
    def team_leave(team_id: str, body: TeamLeave, current=Depends(actor)):
        return messaging.leave(current, team_id, body)

    @app.post('/v1/teams/{team_id}/members/{action}')
    def team_manage(team_id: str, action: str, body: TeamTarget, current=Depends(actor)):
        return messaging.manage_member(current, team_id, body, action)

    @app.get('/v1/messages/{kind}/{target}')
    def message_list(kind: str, target: str, after: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807), limit: int | None = Query(None, ge=1, le=100),
                     before: int | None = Query(None, ge=1, le=9_223_372_036_854_775_807), tail: bool = False, current=Depends(actor)):
        if tail or before is not None:
            if after is not None:
                raise ServiceError(422, 'invalid_request')
            return messaging.message_window(current, kind, target, before=before, tail=tail, limit=8 if limit is None else limit)
        return messaging.messages(current, kind, target, 0 if after is None else after, 50 if limit is None else limit)

    @app.post('/v1/messages/{kind}/{target}')
    def message_send(kind: str, target: str, body: SendMessage, current=Depends(actor)):
        return messaging.send(current, kind, target, body)

    @app.post('/v1/messages/{kind}/{target}/read')
    def message_read(kind: str, target: str, body: ReadMessages, current=Depends(actor)):
        return messaging.mark_read(current, kind, target, body)

    @app.post('/v1/reports')
    def message_report(body: ReportMessage, current=Depends(actor)):
        return messaging.report(current, body)

    @app.get('/internal/v1/moderation/reports')
    def moderation_reports(after: str = '', limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return messaging.moderation_queue(current, after, limit)

    @app.post('/internal/v1/moderation/messages')
    def moderation_action(body: ModerateMessage, current=Depends(actor)):
        return messaging.moderate(current, body)

    @app.post('/v1/ugc/reports')
    def ugc_report(body: UgcReport, current=Depends(actor)):
        return ugc.report(current, body)

    @app.get('/internal/v1/moderation/ugc/reports')
    def ugc_queue(after: str = '', limit: int = Query(50, ge=1, le=100), current=Depends(actor)):
        return ugc.queue(current, after, limit)

    @app.post('/internal/v1/moderation/ugc/actions')
    def ugc_action(body: UgcModerate, current=Depends(actor)):
        return ugc.moderate(current, body)

    async def receive_notification(request, sandbox):
        if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
            return JSONResponse({'error': 'invalid_content_type'}, status_code=415)
        # An environment URL cannot forward a live event into a sandbox catalog.
        if commerce.config.sandbox is not sandbox:
            return JSONResponse({'error': 'notification_environment_unavailable'}, status_code=503)
        body = await request.body()
        return await run_in_threadpool(notifications.receive, body, source(request))

    @app.post('/v1/commerce/notifications/rustore/sandbox')
    async def sandbox_notification(request: Request):
        return await receive_notification(request, True)

    @app.post('/v1/commerce/notifications/rustore/production')
    async def production_notification(request: Request):
        return await receive_notification(request, False)

    @app.get('/v1/me', description='Reward-credit totals only. This is not a synchronized gameplay wallet or profile-import endpoint.')
    def me(current=Depends(actor)):
        return authority.account(current)

    @app.get('/v1/daily-gift/offer')
    def offer(current=Depends(actor)):
        return authority.daily_offer(current)

    @app.post('/v1/daily-gift/claim')
    def claim(request: GiftRequest, current=Depends(actor)):
        return authority.daily_claim(current, request)

    @app.get('/v1/rewards')
    def rewards(after: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(100, ge=1, le=100), current=Depends(actor)):
        return authority.rewards(current, after, limit)

    @app.get('/v1/wellworks')
    def wellworks(current=Depends(actor)):
        return authority.wellworks_view(current)

    @app.post('/v1/wellworks/claim')
    def wellworks_claim(request: MilestoneRequest, current=Depends(actor)):
        return authority.wellworks_claim(current, request)

    @app.get('/v1/rain-cup')
    def cup(current=Depends(actor)):
        return authority.cup_view(current)

    @app.post('/v1/rain-cup/join')
    def cup_join(request: Command, current=Depends(actor)):
        return authority.cup_join(current, request)

    @app.post('/v1/rain-cup/claim')
    def cup_claim(request: CupClaimRequest, current=Depends(actor)):
        return authority.cup_claim(current, request)

    @app.post('/v1/audit-events', description='Explicit client-reported diagnostics. Never grants currency, verifies wins or advances progression.')
    def events(request: EventBatch, current=Depends(actor)):
        return authority.ingest(current, request)

    @app.post('/internal/v1/verified-first-clear', description='Requires a separately provisioned verifier credential. Trusts an upstream gameplay verifier; this service does not itself validate a board replay or proof digest.')
    def verified_clear(request: VerifiedClear, current=Depends(verifier)):
        if replay.enabled: raise ServiceError(409, 'use_verified_gameplay')
        return authority.verified_clear(current, request)

    @app.get('/v1/commerce/catalog', description='Disabled until explicitly configured; sandbox confirmations credit the staging server wallet. Ordinary Unity profile integration and live checkout remain disabled.')
    def commerce_catalog(current=Depends(actor)):
        return commerce.catalog(current)

    @app.post('/v1/commerce/orders')
    def commerce_create(request: CreateCommerceOrder, current=Depends(actor)):
        return commerce.create(current, request)

    @app.get('/v1/commerce/orders/pending', description='Player-scoped recovery of unsettled orders, refunds under review and confirmations awaiting provider delivery acknowledgement.')
    def commerce_pending(after: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(100, ge=1, le=100), current=Depends(actor)):
        return commerce.pending(current, after, limit)

    @app.get('/v1/commerce/orders/{order_id}')
    def commerce_order(order_id: str, current=Depends(actor)):
        return commerce.order(current, order_id)

    @app.post('/v1/commerce/orders/{order_id}/reconcile', description='Queries the configured store provider. Client status, price and grant fields are rejected. Only matching confirmed invoices create one durable server credit.')
    def commerce_reconcile(order_id: str, request: ReconcileCommerceOrder, current=Depends(actor)):
        return commerce.reconcile(current, order_id, request)

    from .sdk_commerce_schemas125 import SdkPurchaseReport125

    @app.post('/v1/commerce/orders/{order_id}/sdk-report',
              description='Explicit SDK client-reported fulfillment only. Device authentication does not prove payment. Frozen order correlation and unique receipts grant inventory once; no provider API call.')
    def commerce_sdk_report(order_id: str, request: SdkPurchaseReport125, current=Depends(actor)):
        return commerce.sdk_report(current, order_id, request)

    @app.get('/v1/commerce/credits')
    def commerce_credits(after: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(100, ge=1, le=100), current=Depends(actor)):
        return commerce.credits(current, after, limit)

    @app.get('/v1/wallet', description='Staging server wallet; ordinary Unity local profiles remain unmigrated.')
    def wallet_view(current=Depends(actor)):
        return wallet.view(current)

    @app.get('/v1/wallet/ledger')
    def wallet_ledger(after: int = Query(0, ge=0, le=9_223_372_036_854_775_807), limit: int = Query(100, ge=1, le=100), current=Depends(actor)):
        return wallet.ledger(current, after, limit)

    @app.post('/v1/wallet/refill')
    def wallet_refill(request: WalletCommand, current=Depends(actor)):
        return wallet.refill(current, request)

    @app.post('/v1/attempts/reserve')
    def reserve_attempt(request: ReserveAttempt, current=Depends(actor)):
        return bound_attempts.reserve(current, request) if bound_attempts else wallet.reserve(current, request)

    @app.get('/v1/attempts/{attempt_id}')
    def get_attempt(attempt_id: str, current=Depends(actor)):
        return wallet.attempt(current, attempt_id)

    @app.post('/v1/attempts/{attempt_id}/start')
    def start_attempt(attempt_id: str, request: WalletCommand, current=Depends(actor)):
        return bound_attempts.start(current, attempt_id, request) if bound_attempts else wallet.command(current, attempt_id, 'start', request)

    @app.post('/v1/attempts/{attempt_id}/quit')
    def quit_attempt(attempt_id: str, request: WalletCommand, current=Depends(actor)):
        if replay.enabled: return replay.abandon(current, attempt_id, request)
        return wallet.command(current, attempt_id, 'quit', request)

    @app.post('/v1/attempts/{attempt_id}/continue')
    def continue_attempt(attempt_id: str, request: WalletCommand, current=Depends(actor)):
        return wallet.command(current, attempt_id, 'continue', request)

    @app.post('/v1/attempts/{attempt_id}/tools')
    def spend_tool(attempt_id: str, request: SpendTool, current=Depends(actor)):
        return wallet.command(current, attempt_id, 'tool', request)

    @app.post('/internal/v1/attempts/settle', description='Separately provisioned upstream verifier only. This service does not validate a board replay; player outcome submissions are forbidden.')
    def settle_attempt(request: SettleAttempt, current=Depends(verifier)):
        return wallet.settle(current, request)

    def replay_response(value):
        return JSONResponse(value, status_code=202 if value.get('state') == 'Pending' else 200)

    @app.post('/v1/gameplay/attempts/{attempt_id}/verify')
    def verify_gameplay(attempt_id: str, body: VerifyReplay, current=Depends(actor)):
        return replay_response(replay.submit(current, attempt_id, 'Verify', body))

    @app.post('/v1/gameplay/attempts/{attempt_id}/tool')
    def gameplay_tool(attempt_id: str, body: ReplayTool, current=Depends(actor)):
        return replay_response(replay.submit(current, attempt_id, 'Tool', body))

    @app.post('/v1/gameplay/attempts/{attempt_id}/continue')
    def gameplay_continue(attempt_id: str, body: ReplayContinue, current=Depends(actor)):
        return replay_response(replay.submit(current, attempt_id, 'Continue', body))

    @app.get('/v1/gameplay/attempts/{attempt_id}/operations/{command_id}')
    def gameplay_operation(attempt_id: str, command_id: str, current=Depends(actor)):
        return replay_response(replay.get(current, attempt_id, command_id))

    @app.post('/v1/gameplay/attempts/{attempt_id}/operations/{command_id}/resume')
    def gameplay_resume(attempt_id: str, command_id: str, body: ResumeReplay, current=Depends(actor)):
        return replay_response(replay.resume(current, attempt_id, command_id))

    @app.post('/v1/gameplay/attempts/{attempt_id}/abandon')
    def gameplay_abandon(attempt_id: str, body: WalletCommand, current=Depends(actor)):
        return replay.abandon(current, attempt_id, body)

    if active_staging_permit is not None:
        # The ASGI request can be cancelled while FastAPI's synchronous
        # endpoint/dependency is still running in a worker thread. Fence the
        # actual work, not only the request middleware lifetime.
        from .staging_versioned_runtime117 import fence_routes
        fence_routes(app, active_staging_permit, notifications, (
            ('/v1/commerce/notifications/rustore/sandbox', sandbox_notification),
            ('/v1/commerce/notifications/rustore/production', production_notification),
        ))
    if production_permit is not None:
        from .production_runtime122 import fence_routes as fence_production_routes
        fence_production_routes(app, production_permit, notifications, (
            ('/v1/commerce/notifications/rustore/sandbox', sandbox_notification),
            ('/v1/commerce/notifications/rustore/production', production_notification),
        ))
    return app
