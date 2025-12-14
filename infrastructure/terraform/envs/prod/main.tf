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

  katest_service_name = "katest-bot-${local.environment}"
}

module "ecr" {
  source      = "../../modules/ecr"
  environment = local.environment

  repositories = [
    {
      name             = local.katest_service_name
      image_mutability = "MUTABLE"
    },

  ]

  image_retention_count = 2
  tags                  = local.common_tags
}

