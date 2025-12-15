variable "environment" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to resources"
  default     = {}
}

variable "service_name" {
  type        = string
  description = "Name of the App Runner service"
}

variable "ecr_repository_url" {
  type        = string
  description = "URL of the ECR repository"
}

variable "image_tag" {
  type        = string
  description = "Tag of the container image to deploy"
  default     = "latest"
}

variable "container_port" {
  type        = number
  description = "Port the container will listen on"
  default     = 8000
}

variable "start_command" {
  type        = string
  description = "Command to start the application"
  default     = null
}

variable "cpu" {
  type        = string
  description = "CPU units for the service"
  default     = "1024"
}

variable "memory" {
  type        = string
  description = "Memory for the service in MB"
  default     = "2048"
}

variable "restrict_to_api_gateway" {
  type        = bool
  description = "If true, security group will only allow traffic from API Gateway IPs. If false, allows traffic on ports 80, 443, and 8000 from anywhere."
  default     = false
}

variable "environment_variables" {
  type        = map(string)
  description = "Non-sensitive environment variables for the container"
  default     = {}
}

variable "auto_deployments_enabled" {
  type        = bool
  description = "Whether to enable auto deployments"
  default     = false
}

variable "vpc_connector_arn" {
  type        = string
  description = "ARN of the VPC connector"
  default     = null
}


variable "auto_scaling_configuration_arn" {
  type        = string
  description = "ARN of the App Runner auto scaling configuration"
  default     = null
}


variable "health_path" {
  type        = string
  description = "Health check path service"
  default     = null
}

variable "max_concurrency" {
  type        = number
  description = "Maximum number of concurrent requests"
  default     = 100
}

variable "max_size" {
  type        = number
  description = "Maximum number of instances"
  default     = 10
}

variable "min_size" {
  type        = number
  description = "Minimum number of instances"
  default     = 1
}

variable "create_vpc_connector" {
  type        = bool
  description = "Whether to create VPC connector"
  default     = false
}
variable "vpc_id" {
  type        = string
  description = "VPC ID for the VPC connector"
  default     = null
}


variable "is_publicly_accessible" {
  type        = bool
  description = "Whether the service is publicly accessible"
  default     = true
}
variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the VPC connector"
  default     = []
}

variable "existing_security_group_id" {
  type        = string
  description = "Existing security group ID to attach to the VPC connector. If set, the module will not create a new one."
  default     = null
}

variable "custom_domain_name" {
  type        = string
  description = "Custom domain name for the App Runner service"
  default     = null
}

