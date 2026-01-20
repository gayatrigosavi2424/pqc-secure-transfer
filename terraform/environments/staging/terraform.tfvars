# Staging environment configuration
environment = "staging"
cloud_provider = "aws"
instance_count = 2
instance_size = "medium"
enable_autoscaling = true
pqc_algorithm = "Kyber768"

# AWS-specific settings
aws_region = "us-west-2"
aws_instance_type = "t3.large"

# Resource limits for staging
max_instances = 10
min_instances = 2
cpu_limit = "2000m"
memory_limit = "4Gi"

# Security settings
enable_encryption_at_rest = true
enable_encryption_in_transit = true
key_rotation_days = 14

# Monitoring settings
enable_detailed_monitoring = true
log_retention_days = 30