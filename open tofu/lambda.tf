# Package du code Lambda en zip
data "archive_file" "lambda_dir" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/output/function.zip"
}

# Fonction Lambda
resource "aws_lambda_function" "lambda_function" {
  filename         = data.archive_file.lambda_dir.output_path
  function_name    = "postagram-label-detector"
  role             = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LabRole"
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_dir.output_base64sha256
  memory_size      = 512
  timeout          = 30
  runtime          = "python3.13"

  environment {
    variables = {
      # Nom de la table DynamoDB passé en variable d'environnement
      table = aws_dynamodb_table.basic-dynamodb-table.name
    }
  }

  tags = {
    Application = "postagram"
  }
}

# Permission : autoriser S3 à invoquer la Lambda
resource "aws_lambda_permission" "allow_from_S3" {
  action         = "lambda:InvokeFunction"
  statement_id   = "AllowExecutionFromS3Bucket"
  function_name  = aws_lambda_function.lambda_function.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = aws_s3_bucket.bucket.arn
  source_account = data.aws_caller_identity.current.account_id
  depends_on     = [aws_lambda_function.lambda_function, aws_s3_bucket.bucket]
}

# Notification S3 : déclencher la Lambda à chaque création d'objet
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.lambda_function.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_from_S3]
}
