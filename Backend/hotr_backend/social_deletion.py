"""Remove social visibility/content in the account-deletion transaction.

Financial receipts, identity replay tombstones and backups have a separate
retention policy. This is not a claim of immediate deletion from all storage.
"""


def close_social_account(db, player, now):
    from .team_life110 import close_member_requests, close_team_requests
    # Search cursors contain an actor-bound query digest and scan position.
    # Remove them in the same transaction as the other social data so an
    # account-deletion rollback also restores every cursor.
    db.execute('DELETE FROM friend_search_cursors WHERE player_id=?', (player,))
    # Invitations are social contact records, not financial entitlements.
    db.execute('DELETE FROM team_invitations WHERE sender_id=? OR recipient_id=?', (player, player))
    # Keep financial claim audit/ownership but erase private mailbox content in
    # the same deletion transaction; account access is revoked by the caller.
    db.execute("UPDATE team_mail SET sender_label='',title='',body='' WHERE player_id=?", (player,))
    for row in db.execute("SELECT team_id FROM team_life_requests WHERE player_id=? AND close_reason='None'", (player,)).fetchall():
        close_member_requests(db, player, row['team_id'], now)
    membership = db.execute('SELECT team_id FROM social_team_members WHERE player_id=?', (player,)).fetchone()
    if membership:
        team = db.execute('SELECT * FROM social_teams WHERE id=?', (membership['team_id'],)).fetchone()
        if team and team['owner_id'] == player:
            # Deletion cannot silently grant a different member moderation
            # powers. Close the owned team and release every member instead.
            close_team_requests(db, team['id'], now)
            db.execute("UPDATE social_teams SET active=0,name='Closed team',description='',updated_at=? WHERE id=?", (now, team['id']))
            db.execute('DELETE FROM social_team_members WHERE team_id=?', (team['id'],))
        db.execute('DELETE FROM social_team_members WHERE player_id=?', (player,))
    db.execute('DELETE FROM social_profiles WHERE player_id=?', (player,))
    db.execute('DELETE FROM social_friend_requests WHERE low_id=? OR high_id=?', (player, player))
    db.execute('DELETE FROM social_blocks WHERE blocker_id=? OR blocked_id=?', (player, player))
    db.execute("UPDATE social_messages SET visibility='Deleted',body='' WHERE author_id=?", (player,))
    db.execute("UPDATE social_reports SET details='',state='Resolved',updated_at=? WHERE reporter_id=?", (now, player))
    db.execute("UPDATE social_ugc_reports SET details='',state='Resolved',updated_at=? WHERE reporter_id=? OR (kind='Profile' AND target_id=?)", (now, player, player))
    db.execute('DELETE FROM social_message_reads WHERE player_id=?', (player,))
    db.execute('DELETE FROM social_moderators WHERE credential_digest IN(SELECT digest FROM credentials WHERE player_id=?)', (player,))
    db.execute("DELETE FROM commands WHERE player_id=? AND operation LIKE 'social.%'", (player,))
