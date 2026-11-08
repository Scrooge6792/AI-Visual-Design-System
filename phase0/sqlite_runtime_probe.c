#include <sqlite3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void fail(sqlite3 *db, const char *step, int rc) {
    fprintf(stderr, "%s: rc=%d message=%s\n", step, rc, db ? sqlite3_errmsg(db) : "no database");
    exit(1);
}

static void exec_sql(sqlite3 *db, const char *sql) {
    char *error = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &error);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "sql: %s\n", error ? error : "unknown error");
        sqlite3_free(error);
        fail(db, "sqlite3_exec", rc);
    }
}

int main(void) {
    sqlite3 *db = NULL;
    int rc = sqlite3_open_v2("/tmp/avds-phase0-runtime.sqlite", &db,
                             SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX,
                             NULL);
    if (rc != SQLITE_OK) fail(db, "open", rc);

    sqlite3_busy_timeout(db, 5000);
    exec_sql(db, "PRAGMA journal_mode=DELETE;"
                 "PRAGMA synchronous=FULL;"
                 "PRAGMA foreign_keys=ON;"
                 "CREATE VIRTUAL TABLE IF NOT EXISTS probe_fts USING fts5(body);"
                 "DELETE FROM probe_fts;"
                 "INSERT INTO probe_fts(body) VALUES ('雪景 逆光 城市雨夜');");

    sqlite3_stmt *stmt = NULL;
    rc = sqlite3_prepare_v2(db,
        "SELECT sqlite_version(), sqlite_compileoption_used('ENABLE_FTS5'),"
        " (SELECT count(*) FROM probe_fts WHERE probe_fts MATCH '雪景'),"
        " (SELECT count(*) FROM probe_fts WHERE probe_fts MATCH '逆光'),"
        " (SELECT journal_mode FROM pragma_journal_mode),"
        " (SELECT synchronous FROM pragma_synchronous),"
        " (SELECT foreign_keys FROM pragma_foreign_keys),"
        " (SELECT timeout FROM pragma_busy_timeout)", -1, &stmt, NULL);
    if (rc != SQLITE_OK) fail(db, "prepare", rc);
    rc = sqlite3_step(stmt);
    if (rc != SQLITE_ROW) fail(db, "step", rc);

    printf("sqlite=%s\nfts5=%d\nshort_zh_snow=%d\nshort_zh_backlight=%d\n"
           "journal=%s\nsynchronous=%d\nforeign_keys=%d\nbusy_timeout=%d\n",
           sqlite3_column_text(stmt, 0), sqlite3_column_int(stmt, 1),
           sqlite3_column_int(stmt, 2), sqlite3_column_int(stmt, 3),
           sqlite3_column_text(stmt, 4), sqlite3_column_int(stmt, 5),
           sqlite3_column_int(stmt, 6), sqlite3_column_int(stmt, 7));

    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return 0;
}
