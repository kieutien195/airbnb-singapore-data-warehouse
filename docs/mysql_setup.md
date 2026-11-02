# MySQL setup (Task 1.5)

This project uses MySQL 8.0 and the database `airbnb_sg_2026`. MySQL Workbench is the client; the Windows `MySQL80` service is the database server. The server must be running before Python or Power BI can connect.

## 1. Start and initialize the server

1. On Windows, open **Services** (`Win + R` → `services.msc`), find `MySQL80`, and choose **Start** if it is stopped. Set Startup type to **Automatic** if the machine should keep MySQL available after restart.
2. Open MySQL Workbench and connect to the local server using an administrator account.
3. Open `sql/00_init_database.sql` in Workbench and execute the whole script. It creates or sets the database default to `utf8mb4` / `utf8mb4_0900_ai_ci`, reports the server/database settings, then creates, queries and drops a temporary test table. It does not contain credentials and does not convert existing table columns.
4. Confirm the result shows MySQL 8.0+, database `airbnb_sg_2026`, charset `utf8mb4`, and a successful Vietnamese text round-trip.

MySQL stores a database-level character set and collation; new tables inherit those defaults unless their definitions override them. Existing tables need their own migration if they were created with another charset. See the [MySQL character set documentation](https://dev.mysql.com/doc/refman/8.0/en/charset-database.html).

## 2. Create separate least-privilege accounts

Do not use the `root` account in Python or Power BI. In Workbench, connect as administrator, open a query tab, replace each password placeholder locally with a unique strong password, then execute the statements. Do not save or commit a query tab containing a real password.

```sql
CREATE USER IF NOT EXISTS 'airbnb_app'@'localhost'
  IDENTIFIED BY '<replace-with-a-unique-local-password>';
GRANT SELECT, INSERT, UPDATE, DELETE
  ON airbnb_sg_2026.* TO 'airbnb_app'@'localhost';

CREATE USER IF NOT EXISTS 'airbnb_bi'@'localhost'
  IDENTIFIED BY '<replace-with-a-different-unique-password>';
GRANT SELECT, SHOW VIEW
  ON airbnb_sg_2026.* TO 'airbnb_bi'@'localhost';

SHOW GRANTS FOR 'airbnb_app'@'localhost';
SHOW GRANTS FOR 'airbnb_bi'@'localhost';
```

`airbnb_app` can read and write project tables; keep schema DDL under the administrator account. `airbnb_bi` is read-only for Power BI. The grants are restricted to this project database, not `*.*`. MySQL account privileges can be limited to a database with `GRANT ... ON database.*`; see the [MySQL GRANT reference](https://dev.mysql.com/doc/refman/8.0/en/grant.html).

## 3. Configure local Python and Power BI

1. Copy `.env.example` to `.env` in the repository root.
2. Set `MYSQL_HOST=localhost`, `MYSQL_PORT=3306`, `MYSQL_DATABASE=airbnb_sg_2026`, and the local `airbnb_app` credentials. Keep `.env` private; `.gitignore` excludes it.
3. With the project virtual environment active, run:

   ```powershell
   python scripts/mysql_connection_test.py
   ```

   A successful run prints the server version, selected database and connection charset/collation. It never prints the password or complete connection URL.
4. Install Oracle MySQL Connector/NET if the MySQL connector is not available in Power BI Desktop. In Power BI Desktop, choose **Get Data → MySQL database**, enter `127.0.0.1:3306`, choose database `airbnb_sg_2026`, and authenticate as `airbnb_bi`. Do not use `airbnb_app` or `root` for the dashboard. Microsoft's connector prerequisites require Oracle MySQL Connector/NET for Power BI Desktop: [Power Query MySQL connector](https://learn.microsoft.com/en-us/power-query/connectors/mysqldatabase).

The project driver uses PyMySQL through SQLAlchemy, and requests `utf8mb4` on its connection. Keep credentials in the local `.env` or Power BI's credential store; never put them in SQL scripts, notebooks, screenshots, commits, or chat.

## 4. Test from another member's computer

For a local-only database, `localhost` means the current computer. To let Thái test against Minh's server, both computers must be on an approved private network or VPN. Before enabling remote access:

1. Get Thái's private IP address and confirm the network/VPN permits the connection.
2. Add a dedicated account restricted to that exact source IP (replace the placeholder with the verified IP and choose a separate password):

   ```sql
   CREATE USER 'airbnb_bi'@'<THAI_PRIVATE_IP>'
     IDENTIFIED BY '<unique-password-for-this-host>';
   GRANT SELECT, SHOW VIEW
     ON airbnb_sg_2026.* TO 'airbnb_bi'@'<THAI_PRIVATE_IP>';
   ```

3. Configure MySQL to listen on the private network interface, and add a Windows Firewall inbound rule for TCP 3306 limited to that exact IP. Do not expose port 3306 to the public internet or use a wildcard host (`'%'`).
4. On Thái's computer, use Minh's private IP as the host, port 3306, and the read-only account. Run `SELECT VERSION(), DATABASE();` and confirm it returns MySQL 8.0+ and `airbnb_sg_2026`.
5. After the check, revoke/remove the temporary remote account and firewall rule unless the team has an approved shared-server setup.

Remote access depends on network access and the exact host IP, so it must be completed with the teammate present. Keep the initial setup loopback-only until that coordination happens.

## 5. Make and verify a backup

Use Workbench so the password is not placed in a command line:

1. Choose **Server → Data Export**.
2. Select only `airbnb_sg_2026`, choose **Export to Self-Contained File**, and save under a local `backups/` folder.
3. Start the export and verify Workbench reports completion and the output file is non-empty.
4. Keep the dump outside Git. `/backups/` is ignored by `.gitignore`; never upload a dump containing project or personal data to the repository.
5. For a restore drill, import the dump into a disposable local schema, verify the tables and row counts, then remove that disposable schema only after confirming its name. Do not test restore by overwriting the working database.

MySQL documents `mysqldump` as a logical backup/restore utility; Workbench's Data Export provides the GUI path for this project's first backup check. See [MySQL backup documentation](https://dev.mysql.com/doc/refman/8.0/en/using-mysqldump.html).

## Completion evidence checklist

- [ ] `MySQL80` is running; `SELECT VERSION()` reports MySQL 8.0+.
- [ ] `sql/00_init_database.sql` reports `airbnb_sg_2026` and `utf8mb4` / `utf8mb4_0900_ai_ci`; its temporary test table returns the Vietnamese test value.
- [ ] `airbnb_app` and `airbnb_bi` grants are database-scoped and `SHOW GRANTS` was reviewed.
- [ ] `.env` is local/ignored; Python connection test passes without printing secrets.
- [ ] Power BI can connect with the read-only user (when Power BI is available).
- [ ] Workbench export completes and the dump is kept outside Git.
- [ ] Thái confirms the remote `SELECT VERSION(), DATABASE()` test over the approved private network (requires coordinated network setup).
