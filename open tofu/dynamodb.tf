resource "aws_dynamodb_table" "basic-dynamodb-table" {
  name           = "postagram"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "user"
  range_key      = "id"

  attribute {
    name = "user"
    type = "S"
  }

  attribute {
    name = "id"
    type = "S"
  }
}

output "dynamotablename" {
  description = "The postagram dynamodb table name"
  value       = aws_dynamodb_table.basic-dynamodb-table.name
}
