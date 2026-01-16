provider "aws" {
  region = "us-west-2"
}
data "aws_availability_zones" "available" {
  state = "available"
}


locals {
  project_name = "katest"
  environment  = "prod"

  common_tags = {
    Environment = local.environment
    Project     = "${local.project_name}-${local.environment}"
    ManagedBy   = "terraform"
  }

  katest_service_name = "katest-${local.environment}"
}

