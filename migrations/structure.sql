CREATE OR REPLACE FUNCTION handle_battlepass_level_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE battlepasslevel
    SET level = level - 1
    WHERE guild_id = OLD.guild_id AND level > OLD.level;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION handle_battlepass_level_insert()
RETURNS TRIGGER AS $$
DECLARE 
    max_level INTEGER;
BEGIN
    IF NEW.level IS NULL THEN
        SELECT COALESCE(MAX(level), 0) INTO max_level 
        FROM battlepasslevel 
        WHERE guild_id = NEW.guild_id;
        NEW.level := max_level + 1;
    ELSE
       UPDATE battlepasslevel
       SET level = level + 1
       WHERE guild_id = NEW.guild_id AND level >= NEW.level;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION handle_user_case_update()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount < 1 THEN
        DELETE FROM usercase WHERE id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_case_update
BEFORE UPDATE ON usercase
FOR EACH ROW
EXECUTE FUNCTION handle_user_case_update();

CREATE TRIGGER battlepass_level_delete
AFTER DELETE ON battlepasslevel
FOR EACH ROW
EXECUTE FUNCTION handle_battlepass_level_delete();

CREATE TRIGGER battlepass_level_insert
BEFORE INSERT ON battlepasslevel
FOR EACH ROW
EXECUTE FUNCTION handle_battlepass_level_insert();