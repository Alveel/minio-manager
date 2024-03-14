service_account_policy_base = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:*Object",
                "s3:*ObjectTagging",
                "s3:GetObjectVersion",
                "s3:*ObjectVersionTagging",
                "s3:*BucketNotification",
                "s3:*MultipartUploads",
                "s3:GetBucketLocation",
                "s3:GetBucketObjectLockConfiguration",
                "s3:GetBucketPolicy",
            ],
            "Resource": ["arn:aws:s3:::BUCKET_NAME_REPLACE_ME", "arn:aws:s3:::BUCKET_NAME_REPLACE_ME/*"],
        }
    ],
}
