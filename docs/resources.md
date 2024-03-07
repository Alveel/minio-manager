# Resources

Resources that should be deployed are to be specified in each environments' `resource.yaml`.

There are currently 5 resources supported; `buckets`, `bucket_policies`, `service_accounts`, `iam_policies`, and  `iam_policy_attachments`.

## Buckets

Buckets are used to organize and store objects.

The `resource.yaml` supports the following properties for `buckets`:

| **Property**             | **Required** | **Description**                                                                          | **Default** | **Example**                            |
|--------------------------|--------------|------------------------------------------------------------------------------------------|-------------|----------------------------------------|
| `name`                   | YES          | Specify the name of the bucket                                                           | None        | `infra-test-tomato-bucket`             |
| `create_service_account` | NO           | Do you want to automatically create a service account that has ownership of this bucket? | `TRUE`      | `FALSE`                                |
| `object_lifecycle_file`  | NO           | Specify the lifecycle policy that you want to attach to this bucket                      | None        | `lifecycle_policies/my_lifecycle.json` |
| `versioning`             | NO           | Do you want to enable versioning for this bucket?                                        | `TRUE`      | `FALSE`                                |

## Bucket policies

Bucket policies are used to restrict bucket access or action on a bucket level.

The `resource.yaml` supports the following properties for `bucket_policies`:

| **Property**  | **Required** | **Description**                                                      | **Default** | **Example**                            |
|---------------|--------------|----------------------------------------------------------------------|-------------|----------------------------------------|
| `name`        | YES          | Specify the name of the bucket                                       | None        | `infra-test-tomato-bucket`             |
| `policy_file` | YES          | Specify the name of the policy that should be assigned to the bucket | None        | `bucket_policies/my_bucketpolicy.json` |

## Service accounts

Service accounts are, by default, automatically created when creating a bucket. However, it is possible to create them separately.

The `resource.yaml` supports the following properties for `service_accounts`:

| **Property**  | **Required** | **Description**                                  | **Default** | **Example**                  |
|---------------|--------------|--------------------------------------------------|-------------|------------------------------|
| `name`        | YES          | Specify the name of the service account          | None        | `infra-test-tomato-bucket`   |
| `policy_file` | NO           | Specify the policy file for this service account | None        | `user_policies/my_user.json` |

## IAM policies

IAM policies consist of actions and resources to which an authenticated user has access. Each policy describes one or more actions and conditions that outline the permissions of a user or group of users.

The `resource.yaml` supports the following properties for `iam_policies`:

| **Property**  | **Required** | **Description**                                | **Default** | **Example**                |
|---------------|--------------|------------------------------------------------|-------------|----------------------------|
| `name`        | YES          | Specify the name of the IAM policy             | None        | `infra-test-adminpolicy`   |
| `policy_file` | YES          | Specify the policy file to use for this policy | None        | `iam_policies/my_iam.json` |

## IAM policy attachment

For IAM policies to be effective we have to attach them to users.

The `resource.yaml` supports the following properties for `iam_policy_attachments`:

| **Property** | **Required** | **Description**                                                      | **Default** | **Example** |
|--------------|--------------|----------------------------------------------------------------------|-------------|-------------|
| `username`   | YES          | Specify the username which should get a specific policy assigned     | None        | `my-user`   |
| `policies`   | YES          | Specify a **list** of policies to assign to this specific `username` | None        | `policy-1`  |
