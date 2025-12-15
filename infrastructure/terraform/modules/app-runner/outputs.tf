output "service_url" {
  value = aws_apprunner_service.service.service_url
}

output "service_arn" {
  value = aws_apprunner_service.service.arn
}

output "service_status" {
  value = aws_apprunner_service.service.status
}

output "custom_domain_validation_records" {
  description = "DNS validation records for the custom domain"
  value       = length(aws_apprunner_custom_domain_association.core_custom_domain) > 0 ? aws_apprunner_custom_domain_association.core_custom_domain[0].certificate_validation_records : []
}

output "vpc_connector_arn" {
  description = "ARN of the VPC connector"
  value       = var.create_vpc_connector ? aws_apprunner_vpc_connector.connector[0].arn : var.vpc_connector_arn
}

output "security_group_id" {
  description = "ID of the security group attached to the App Runner service"
  value       = var.existing_security_group_id
}

output "log_group_name" {
  description = "Name of the CloudWatch log group for the App Runner service"
  value       = "/aws/apprunner/${aws_apprunner_service.service.service_name}"
}

output "instance_role_id" {
  description = "ID of the IAM role used by App Runner instances"
  value       = aws_iam_role.app_runner_instance_role.id
}

output "instance_role_arn" {
  description = "ARN of the IAM role used by App Runner instances"
  value       = aws_iam_role.app_runner_instance_role.arn
}