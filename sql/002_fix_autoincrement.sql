-- ============================================================
--  Fix: restore AUTO_INCREMENT on every `id` primary-key column.
--
--  Some MySQL hosts / import tools create the tables with `id INT
--  NOT NULL PRIMARY KEY` but WITHOUT AUTO_INCREMENT, which makes
--  every INSERT fail with:
--      (1364, "Field 'id' doesn't have a default value")
--
--  Safe to run repeatedly. Only touches columns that are missing it.
--
--  Usage:  mysql -u USER -p YOUR_DB < 002_fix_autoincrement.sql
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS akg_fix_ai $$
CREATE PROCEDURE akg_fix_ai()
BEGIN
  DECLARE done INT DEFAULT 0;
  DECLARE tname VARCHAR(64);
  DECLARE cur CURSOR FOR
    SELECT c.TABLE_NAME
    FROM information_schema.COLUMNS c
    WHERE c.TABLE_SCHEMA = DATABASE()
      AND c.COLUMN_NAME = 'id'
      AND c.COLUMN_KEY = 'PRI'
      AND c.EXTRA NOT LIKE '%auto_increment%';
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

  OPEN cur;
  read_loop: LOOP
    FETCH cur INTO tname;
    IF done = 1 THEN LEAVE read_loop; END IF;
    SET @s = CONCAT('ALTER TABLE `', tname, '` MODIFY `id` INT NOT NULL AUTO_INCREMENT');
    PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
  END LOOP;
  CLOSE cur;
END $$

DELIMITER ;

CALL akg_fix_ai();
DROP PROCEDURE IF EXISTS akg_fix_ai;
