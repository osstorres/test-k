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

module "vpc" {
  source = "../../modules/vpc"

  project_name = local.project_name
  environment  = local.environment

  vpc_cidr             = "10.0.0.0/16"
  public_subnets_cidr  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets_cidr = ["10.0.101.0/24", "10.0.102.0/24"]
  availability_zones   = data.aws_availability_zones.available.names

  single_nat_gateway = true

  tags = local.common_tags
}

resource "aws_security_group" "app_runner_vpc" {
  name        = "${local.katest_service_name}-vpc-connector"
  description = "Security group for App Runner VPC connector"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = local.common_tags
}


module "test-k" {
  source = "../../modules/app-runner"

  environment = local.environment
  tags        = local.common_tags

  service_name       = local.katest_service_name
  ecr_repository_url = module.ecr.repository_urls[local.katest_service_name]
  image_tag          = "latest"

  container_port = 8000

  create_vpc_connector   = true
  vpc_id                 = module.vpc.vpc_id
  subnet_ids             = module.vpc.private_subnet_ids
  is_publicly_accessible = true

  existing_security_group_id = aws_security_group.app_runner_vpc.id

  environment_variables = {

  }

  min_size = 1
  max_size = 2
  max_concurrency = 20
  cpu = "1024"
  memory = "2048"
}
