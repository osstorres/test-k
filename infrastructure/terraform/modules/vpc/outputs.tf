output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "vpc_cidr_blocks" {
  description = "List of VPC CIDR blocks including VPC and subnets"
  value       = concat([var.vpc_cidr], var.public_subnets_cidr, var.private_subnets_cidr)
}
