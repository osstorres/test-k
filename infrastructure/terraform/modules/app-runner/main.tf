locals {
  effective_vpc_id = var.vpc_id
}

resource "aws_apprunner_service" "service" {
  service_name = var.service_name

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_service_role.arn
    }

    auto_deployments_enabled = var.auto_deployments_enabled

    image_repository {
      image_configuration {
        port                          = var.container_port
        runtime_environment_variables = var.environment_variables
        start_command                 = var.start_command != null ? var.start_command : null
      }
      image_identifier      = "${var.ecr_repository_url}:${var.image_tag}"
      image_repository_type = "ECR"
    }
  }


  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = aws_iam_role.app_runner_instance_role.arn
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.app_scaling.arn

  network_configuration {
    egress_configuration {
      egress_type = (
        var.create_vpc_connector || var.vpc_connector_arn != null
      ) ? "VPC" : "DEFAULT"

      vpc_connector_arn = var.create_vpc_connector ? aws_apprunner_vpc_connector.connector[0].arn : var.vpc_connector_arn
    }

    ingress_configuration {
      is_publicly_accessible = var.is_publicly_accessible
    }
  }

  depends_on = [
    aws_apprunner_auto_scaling_configuration_version.app_scaling,
    aws_iam_role_policy_attachment.app_runner_service_role_policy,
  ]

  tags = merge(
    {
      Name        = var.service_name
      Environment = var.environment
    },
    var.tags
  )

  health_check_configuration {
    protocol            = var.health_path == null ? "TCP" : "HTTP"
    path                = var.health_path
    timeout             = 19
    interval            = 20
    unhealthy_threshold = 20
    healthy_threshold   = 1
  }
}

# Service Role
resource "aws_iam_role" "app_runner_service_role" {
  name = "${var.service_name}-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "build.apprunner.amazonaws.com",
            "tasks.apprunner.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = var.tags
}

# Instance Role
resource "aws_iam_role" "app_runner_instance_role" {
  name = "${var.service_name}-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "app_runner_service_role_policy" {
  role       = aws_iam_role.app_runner_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
  depends_on = [aws_iam_role.app_runner_service_role]

}

# Secrets Manager access policy
// Removed Secrets Manager IAM policy per requirements


# Auto Scaling Configuration
resource "aws_apprunner_auto_scaling_configuration_version" "app_scaling" {
  auto_scaling_configuration_name = var.service_name

  max_concurrency = var.max_concurrency
  max_size        = var.max_size
  min_size        = var.min_size
  lifecycle {
    create_before_destroy = true

  }
  tags = merge(
    {
      Name = "${var.service_name}-autoscaling"
    },
    var.tags
  )
}

resource "aws_apprunner_custom_domain_association" "core_custom_domain" {
  count       = var.custom_domain_name != null ? 1 : 0
  domain_name = var.custom_domain_name
  service_arn = aws_apprunner_service.service.arn

  enable_www_subdomain = false
}

# VPC connector and security group for private egress (e.g., to RDS)
resource "aws_apprunner_vpc_connector" "connector" {
  count                = var.create_vpc_connector ? 1 : 0
  vpc_connector_name   = "${var.service_name}-vpc-connector"
  subnets              = var.subnet_ids
  security_groups      = [var.existing_security_group_id]
  tags                 = var.tags
}
