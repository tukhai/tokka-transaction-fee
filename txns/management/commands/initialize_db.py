from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Initializes the database with custom tables if they do not exist.'

    def handle(self, *args, **options):
        self.stdout.write("Checking and setting up initial database tables...")

        with connection.cursor() as cursor:
            create_txn_table(cursor, 'transaction_record')
            create_txn_table(cursor, 'transaction_batch_record')

        self.stdout.write("Database setup complete.")


def create_txn_table(cursor, table_name):
    # Check if the table already exists using safe parameterized queries
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename = %s
        );
    """, [table_name])

    if not cursor.fetchone()[0]:
        # Create the table and hypertable using safe formatting for identifiers
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                id serial,
                hash VARCHAR(255),
                block_number BIGINT,
                timestamp TIMESTAMP,
                fee FLOAT,
                PRIMARY KEY (hash, timestamp)
            );
        """)
        cursor.execute("SELECT create_hypertable(%s, 'timestamp');", [table_name])
