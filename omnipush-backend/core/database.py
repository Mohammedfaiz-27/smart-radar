from supabase import create_client, Client
from typing import Optional, Any, Dict, List
import logging
from .config import settings
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase database client wrapper with configurable RLS support"""

    def __init__(self):
        self._client: Optional[Client] = None
        self._service_client: Optional[Client] = None
        self._pg_connection_params: Optional[Dict[str, Any]] = None

    @property
    def client(self) -> Client:
        """
        Get Supabase client based on USE_RLS configuration.
        - If USE_RLS=true: Returns service client (we handle RLS via direct SQL)
        - If USE_RLS=false: Returns service client (bypasses RLS)
        """
        # Always use service client - RLS is handled via direct SQL when enabled
        return self.service_client

    @property
    def service_client(self) -> Client:
        """Get service role Supabase client (always bypasses RLS)"""
        if self._service_client is None:
            self._service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
        return self._service_client

    def _get_pg_connection_params(self) -> Dict[str, Any]:
        """Extract PostgreSQL connection parameters from Supabase URL"""
        if self._pg_connection_params is None:
            # Parse Supabase URL to get database connection details
            # Format: https://xxx.supabase.co -> postgres://postgres:[password]@db.xxx.supabase.co:5432/postgres
            url = settings.supabase_url
            parsed = urlparse(url)
            project_ref = parsed.hostname.split('.')[0]

            self._pg_connection_params = {
                'host': f'db.{project_ref}.supabase.co',
                'port': 5432,
                'database': 'postgres',
                'user': 'postgres',
                'password': settings.supabase_db_password,
            }
        return self._pg_connection_params

    @contextmanager
    def rls_context(self, tenant_id: str):
        """
        Context manager that sets tenant context for RLS-enabled queries.
        Uses direct PostgreSQL connection to maintain session state.

        Usage:
            with db.rls_context(tenant_id):
                # Execute queries here with RLS enabled
                result = db.client.table('tenants').select('*').execute()
        """
        if not settings.use_rls:
            # RLS disabled, just yield
            yield
            return

        conn = None
        try:
            # Get direct PostgreSQL connection
            conn_params = self._get_pg_connection_params()
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Set tenant context
            cursor.execute(
                "SELECT set_config('app.current_tenant_id', %s, false)",
                (str(tenant_id),)
            )

            logger.debug(f"Set RLS tenant context to: {tenant_id}")

            yield cursor

            conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to execute with RLS context: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def query_with_rls(self, tenant_id: str, table: str, select: str = '*', filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query with RLS context set.

        Args:
            tenant_id: The tenant ID to set as context
            table: Table name to query
            select: Columns to select (default: '*')
            filters: Dictionary of column: value filters

        Returns:
            List of rows as dictionaries
        """
        if not settings.use_rls:
            # Use regular Supabase client without RLS
            query = self.service_client.table(table).select(select)
            if filters:
                for col, val in filters.items():
                    query = query.eq(col, val)
            return query.execute().data

        # Use direct SQL with RLS context
        with self.rls_context(tenant_id) as cursor:
            # Build WHERE clause
            where_clause = ""
            params = []
            if filters:
                where_parts = []
                for col, val in filters.items():
                    where_parts.append(f"{col} = %s")
                    params.append(val)
                where_clause = "WHERE " + " AND ".join(where_parts)

            # Execute query
            query = f"SELECT {select} FROM {table} {where_clause}"
            cursor.execute(query, params)

            return cursor.fetchall()

    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            # Simple query to test connection (bypass RLS for health check)
            response = self.service_client.table('tenants').select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.exception(f"Database health check failed: {e}")
            return False


# Global database instance
db = SupabaseClient()


def get_database() -> SupabaseClient:
    """Dependency to get database instance"""
    return db