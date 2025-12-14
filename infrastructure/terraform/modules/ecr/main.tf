resource "aws_ecr_repository" "repositories" {
  for_each             = { for repo in var.repositories : repo.name => repo }
  name                 = each.value.name
  image_tag_mutability = each.value.image_mutability
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }


  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = merge(
    {
      Name        = each.value.name
      Environment = var.environment
    },
    var.tags
  )
}

resource "aws_ecr_lifecycle_policy" "policy" {
  for_each   = aws_ecr_repository.repositories
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.image_retention_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.image_retention_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
