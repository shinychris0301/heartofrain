"""Additive full-inventory order terms and stable-player Special eligibility."""

COMMERCE_V9_DDL = '''
ALTER TABLE commerce_orders ADD COLUMN grant_json TEXT;
ALTER TABLE commerce_orders ADD COLUMN creation_command_id TEXT;
ALTER TABLE commerce_orders ADD COLUMN purchase_limit INTEGER CHECK(purchase_limit IS NULL OR purchase_limit=1);
ALTER TABLE commerce_orders ADD COLUMN reservation_released INTEGER NOT NULL DEFAULT 0 CHECK(reservation_released IN (0,1));
ALTER TABLE commerce_credits ADD COLUMN grant_json TEXT;
CREATE TABLE commerce_entitlements (
 player_id TEXT NOT NULL REFERENCES players(id), offer_id TEXT NOT NULL,
 order_id TEXT NOT NULL UNIQUE REFERENCES commerce_orders(id),
 state TEXT NOT NULL CHECK(state IN ('Reserved','Consumed')),
 updated_at INTEGER NOT NULL, PRIMARY KEY(player_id,offer_id));
UPDATE commerce_orders SET grant_json='{"coins":'||coins||',"stars":0,"starting":[0,0,0,0],"tools":[0,0,0,0]}';
UPDATE commerce_credits SET grant_json='{"coins":'||coins||',"stars":0,"starting":[0,0,0,0],"tools":[0,0,0,0]}';
'''
