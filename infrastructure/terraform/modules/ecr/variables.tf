variable "environment" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to resources"
  default     = {}
}

variable "repositories" {
  description = "List of ECR repositories to create"
  type = list(object({
    name             = string
    image_mutability = string
  }))
}

variable "image_retention_count" {
  type        = number
  description = "Number of images to retain"
  default     = 10
}

