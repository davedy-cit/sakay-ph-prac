-- Run once when the MySQL container initialises an empty data directory.
-- Django's test database is named test_sakayph (config/settings.py TEST.NAME);
-- the sakayph application user needs rights on it so `manage.py test` can
-- create and drop it. Grants on sakayph itself come from the container's
-- bootstrap (MYSQL_USER) plus application code.
GRANT ALL PRIVILEGES ON `test_sakayph`.* TO 'sakayph'@'%';
FLUSH PRIVILEGES;
