#!/usr/bin/env python3
"""
Test runner and environment setup for DBLink MCP Server
"""
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))
import time
import os
import asyncio
import psycopg2
import cx_Oracle
from dblink_mcp.server import DatabaseManager

def check_docker_compose():
    """Check if Docker Compose is available"""
    try:
        subprocess.run(['docker-compose', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(['docker', 'compose', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

def start_test_environment():
    """Start the Docker Compose test environment"""
    if not check_docker_compose():
        print("❌ Docker Compose not found. Please install Docker Compose.")
        return False
    
    print("🚀 Starting test database environment...")
    
    # Try docker-compose first, then docker compose
    compose_cmd = ['docker-compose']
    try:
        subprocess.run(compose_cmd + ['--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        compose_cmd = ['docker', 'compose']
    
    try:
        subprocess.run(compose_cmd + ['up', '-d'], check=True)
        print("✅ Docker containers started")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start containers: {e}")
        return False

def wait_for_databases():
    """Wait for databases to be ready"""
    print("⏳ Waiting for databases to be ready...")
    
    # Wait for PostgreSQL
    postgres_ready = False
    for attempt in range(30):  # 30 seconds timeout
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='testdb',
                user='testuser',
                password='testpass'
            )
            conn.close()
            postgres_ready = True
            print("✅ PostgreSQL is ready")
            break
        except psycopg2.OperationalError:
            time.sleep(1)
    
    if not postgres_ready:
        print("❌ PostgreSQL not ready after 30 seconds")
        return False
    
    # Wait for Oracle
    oracle_ready = False
    for attempt in range(60):  # 60 seconds timeout (Oracle takes longer)
        try:
            dsn = cx_Oracle.makedsn('localhost', 1521, service_name='TESTDB')
            conn = cx_Oracle.connect(user='testuser', password='testpass', dsn=dsn)
            conn.close()
            oracle_ready = True
            print("✅ Oracle is ready")
            break
        except cx_Oracle.DatabaseError:
            time.sleep(1)
    
    if not oracle_ready:
        print("❌ Oracle not ready after 60 seconds")
        return False
    
    return True

def stop_test_environment():
    """Stop the Docker Compose test environment"""
    print("🛑 Stopping test database environment...")
    
    compose_cmd = ['docker-compose']
    try:
        subprocess.run(compose_cmd + ['--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        compose_cmd = ['docker', 'compose']
    
    try:
        subprocess.run(compose_cmd + ['down'], check=True)
        print("✅ Docker containers stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to stop containers: {e}")

def run_unit_tests():
    """Run unit tests only"""
    print("🧪 Running unit tests...")
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_mcp_server.py', 
        '-v', '--tb=short'
    ])
    return result.returncode == 0

def run_integration_tests():
    """Run integration tests"""
    print("🔗 Running integration tests...")
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_integration.py', 
        '-v', '--tb=short', '-m', 'integration'
    ])
    return result.returncode == 0

def run_all_tests():
    """Run both unit and integration tests"""
    print("🧪 Running all tests...")
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/', 
        '-v', '--tb=short'
    ])
    return result.returncode == 0

async def test_mcp_functionality():
    """Test core MCP functionality with live databases"""
    print("🔧 Testing MCP functionality...")
    
    try:
        manager = DatabaseManager()
        
        # Test PostgreSQL connection
        postgres_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        await manager.add_connection('test_pg', 'postgresql', postgres_config)
        
        # Test Oracle connection
        oracle_config = {
            'host': 'localhost',
            'port': 1521,
            'service_name': 'TESTDB',
            'user': 'testuser',
            'password': 'testpass'
        }
        await manager.add_connection('test_oracle', 'oracle', oracle_config)
        
        # Test queries
        pg_result = await manager.execute_query('test_pg', 'SELECT COUNT(*) as count FROM testschema.employees')
        oracle_result = await manager.execute_query('test_oracle', 'SELECT COUNT(*) as count FROM testschema.employees')
        
        print(f"✅ PostgreSQL query returned {len(pg_result)} rows")
        print(f"✅ Oracle query returned {len(oracle_result)} rows")
        
        # Clean up
        await manager.remove_connection('test_pg')
        await manager.remove_connection('test_oracle')
        
        return True
        
    except Exception as e:
        print(f"❌ MCP functionality test failed: {e}")
        return False

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DBLink MCP Test Runner')
    parser.add_argument('--unit-only', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration-only', action='store_true', help='Run integration tests only')
    parser.add_argument('--no-docker', action='store_true', help='Skip Docker environment setup')
    parser.add_argument('--quick-test', action='store_true', help='Quick MCP functionality test')
    
    args = parser.parse_args()
    
    success = True
    
    if args.unit_only:
        success = run_unit_tests()
    elif args.integration_only or args.quick_test:
        if not args.no_docker:
            if not start_test_environment():
                return 1
            
            if not wait_for_databases():
                stop_test_environment()
                return 1
        
        if args.quick_test:
            success = asyncio.run(test_mcp_functionality())
        else:
            success = run_integration_tests()
        
        if not args.no_docker:
            stop_test_environment()
    else:
        # Run all tests
        if not start_test_environment():
            return 1
        
        if not wait_for_databases():
            stop_test_environment()
            return 1
        
        success = run_all_tests()
        
        stop_test_environment()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())