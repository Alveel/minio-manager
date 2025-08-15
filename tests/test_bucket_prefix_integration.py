"""Integration test for bucket prefix validation.

This test verifies that bucket prefix validation works correctly at the resource parsing stage,
which is the actual implementation location (not in bucket_handler.py).
"""

import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

import pytest

from minio_manager.classes.resource_parser import ClusterResources
from minio_manager.classes.settings import Settings


class TestBucketPrefixIntegration:
    """Integration tests for bucket prefix validation during resource parsing."""
    
    def create_test_resources_yaml(self, buckets: list) -> Path:
        """Create a temporary YAML file with bucket configurations."""
        test_data = {
            "buckets": buckets
        }
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(test_data, temp_file, default_flow_style=False)
        temp_file.close()
        
        return Path(temp_file.name)
    
    def test_bucket_prefix_filtering_with_allowed_prefixes(self):
        """Test that only buckets with allowed prefixes are parsed from YAML."""
        # Create test YAML with mixed bucket names
        buckets_config = [
            {"name": "test-bucket-1", "versioning": True},
            {"name": "production-bucket", "versioning": False},  # Should be filtered out
            {"name": "demo-bucket-1", "versioning": True},
            {"name": "staging-data", "versioning": True},       # Should be filtered out
            {"name": "test-analytics", "versioning": False},
        ]
        
        resources_file = self.create_test_resources_yaml(buckets_config)
        
        try:
            # Parse resources with mocked settings
            cluster_resources = ClusterResources()
            
            with patch('minio_manager.classes.resource_parser.settings') as mock_settings:
                mock_settings.allowed_bucket_prefixes = ("test-", "demo-")
                mock_settings.auto_create_service_account = False
                mock_settings.default_bucket_versioning = "Enabled"
                mock_settings.default_lifecycle_policy_file = None
                
                with patch('sys.exit'):
                    cluster_resources.parse_resources(str(resources_file))
            
            # Verify only allowed buckets were parsed
            parsed_buckets = cluster_resources.buckets
            assert len(parsed_buckets) == 3  # Only test- and demo- prefixed buckets
            
            parsed_names = [bucket.name for bucket in parsed_buckets]
            assert "test-bucket-1" in parsed_names
            assert "demo-bucket-1" in parsed_names  
            assert "test-analytics" in parsed_names
            
            # Verify filtered buckets are NOT in parsed results
            assert "production-bucket" not in parsed_names
            assert "staging-data" not in parsed_names
            
        finally:
            # Clean up temporary file
            resources_file.unlink()
    
    def test_bucket_prefix_filtering_no_restrictions(self):
        """Test that all buckets are parsed when no prefix restrictions are set."""
        # Create test YAML with various bucket names
        buckets_config = [
            {"name": "any-bucket-name", "versioning": True},
            {"name": "production-data", "versioning": False},
            {"name": "development-test", "versioning": True},
            {"name": "no-prefix", "versioning": False},
        ]
        
        resources_file = self.create_test_resources_yaml(buckets_config)
        
        try:
            # Parse resources with no prefix restrictions
            cluster_resources = ClusterResources()
            
            with patch('minio_manager.classes.resource_parser.settings') as mock_settings:
                mock_settings.allowed_bucket_prefixes = None  # No restrictions
                mock_settings.auto_create_service_account = False
                mock_settings.default_bucket_versioning = "Enabled"
                mock_settings.default_lifecycle_policy_file = None
                
                with patch('sys.exit'):
                    cluster_resources.parse_resources(str(resources_file))
            
            # Verify all buckets were parsed (no filtering)
            parsed_buckets = cluster_resources.buckets
            assert len(parsed_buckets) == 4
            
            parsed_names = [bucket.name for bucket in parsed_buckets]
            assert "any-bucket-name" in parsed_names
            assert "production-data" in parsed_names
            assert "development-test" in parsed_names
            assert "no-prefix" in parsed_names
            
        finally:
            # Clean up temporary file
            resources_file.unlink()
    
    def test_bucket_prefix_filtering_single_prefix(self):
        """Test bucket filtering with a single allowed prefix."""
        # Create test YAML
        buckets_config = [
            {"name": "project-data", "versioning": True},
            {"name": "project-analytics", "versioning": False},
            {"name": "other-bucket", "versioning": True},        # Should be filtered
            {"name": "project-testing", "versioning": False},
        ]
        
        resources_file = self.create_test_resources_yaml(buckets_config)
        
        try:
            # Parse resources with single prefix
            cluster_resources = ClusterResources()
            
            with patch('minio_manager.classes.resource_parser.settings') as mock_settings:
                mock_settings.allowed_bucket_prefixes = ("project-",)  # Single prefix
                mock_settings.auto_create_service_account = False
                mock_settings.default_bucket_versioning = "Enabled"
                mock_settings.default_lifecycle_policy_file = None
                
                with patch('sys.exit'):
                    cluster_resources.parse_resources(str(resources_file))
            
            # Verify only project- prefixed buckets were parsed
            parsed_buckets = cluster_resources.buckets
            assert len(parsed_buckets) == 3
            
            parsed_names = [bucket.name for bucket in parsed_buckets]
            assert "project-data" in parsed_names
            assert "project-analytics" in parsed_names
            assert "project-testing" in parsed_names
            assert "other-bucket" not in parsed_names
            
        finally:
            # Clean up temporary file
            resources_file.unlink()
    
    def test_bucket_prefix_filtering_case_sensitivity(self):
        """Test that bucket prefix filtering is case-sensitive."""
        # Create test YAML with case variations
        buckets_config = [
            {"name": "Test-bucket", "versioning": True},    # Should match
            {"name": "test-bucket", "versioning": False},   # Should NOT match (wrong case)
            {"name": "TEST-bucket", "versioning": True},    # Should NOT match (wrong case)
        ]
        
        resources_file = self.create_test_resources_yaml(buckets_config)
        
        try:
            # Parse resources with case-sensitive prefix
            cluster_resources = ClusterResources()
            
            with patch('minio_manager.classes.resource_parser.settings') as mock_settings:
                mock_settings.allowed_bucket_prefixes = ("Test-",)  # Case-sensitive
                mock_settings.auto_create_service_account = False
                mock_settings.default_bucket_versioning = "Enabled"
                mock_settings.default_lifecycle_policy_file = None
                
                with patch('sys.exit'):
                    cluster_resources.parse_resources(str(resources_file))
            
            # Verify only exact case match was parsed
            parsed_buckets = cluster_resources.buckets
            assert len(parsed_buckets) == 1
            
            parsed_names = [bucket.name for bucket in parsed_buckets]
            assert "Test-bucket" in parsed_names
            assert "test-bucket" not in parsed_names
            assert "TEST-bucket" not in parsed_names
            
        finally:
            # Clean up temporary file
            resources_file.unlink()
    
    def test_bucket_prefix_filtering_empty_prefixes(self):
        """Test behavior when prefix list is empty."""
        # Create test YAML
        buckets_config = [
            {"name": "any-name", "versioning": True},
            {"name": "another-bucket", "versioning": False},
        ]
        
        resources_file = self.create_test_resources_yaml(buckets_config)
        
        try:
            # Parse resources with empty prefix list
            cluster_resources = ClusterResources()
            
            with patch('minio_manager.classes.resource_parser.settings') as mock_settings:
                mock_settings.allowed_bucket_prefixes = ()  # Empty tuple
                mock_settings.auto_create_service_account = False
                mock_settings.default_bucket_versioning = "Enabled"
                mock_settings.default_lifecycle_policy_file = None
                
                with patch('sys.exit'):
                    cluster_resources.parse_resources(str(resources_file))
            
            # Verify all buckets are allowed when prefix list is empty
            parsed_buckets = cluster_resources.buckets
            assert len(parsed_buckets) == 2
            
            parsed_names = [bucket.name for bucket in parsed_buckets]
            assert "any-name" in parsed_names
            assert "another-bucket" in parsed_names
            
        finally:
            # Clean up temporary file
            resources_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
