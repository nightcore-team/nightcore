DROP FUNCTION IF EXISTS handle_battlepass_level_delete;

DROP FUNCTION IF EXISTS handle_battlepass_level_insert;

DROP FUNCTION IF EXISTS handle_user_case_update;

DROP TRIGGER IF EXISTS user_case_update ON usercase;

DROP TRIGGER IF EXISTS battlepass_level_insert ON battlepasslevel;

DROP TRIGGER IF EXISTS battlepass_level_delete ON battlepasslevel;