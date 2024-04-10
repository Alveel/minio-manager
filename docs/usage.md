# Usage

## Resource configuration format

You can see what parameters each resource accepts in the [Resources documentation][resources] and what they mean.

## Service Account Details

Service accounts are used in order to create buckets, they are also the owner of these buckets. By default, we have a one-on-one relationship between service accounts and buckets.

However, there is an option to give ownership of multiple bucket to one service account. By specifying `create_service_account: False` for a bucket in the environment's `resource.yaml`.
You must then specify the ownership through a `policy_file`:

``` yaml
buckets:
  - name: infra-test-without-sa
    create_service_account: False

service_accounts:
  - name: infra-test-for-multiple-sa
    policy_file: service_account_policies/infra-test-two-buckets.json
```

The Resource section of this json will specify which bucket this service account has ownership of, in this example `infra-test-two-buckets.json`.
The service account will get ownership over 2 buckets and all of its objects:

``` json
            "Resource": [
                "arn:aws:s3:::infra-test-without-sa",
                "arn:aws:s3:::infra-test-without-sa/*",
                "arn:aws:s3:::infra-test-multiple-access",
                "arn:aws:s3:::infra-test-multiple-access/*"
            ]
```

## Automatic service account creation

By default, when you request a bucket with MinIO Manager it will automatically create a MinIO service account that gives access to just that bucket.
It does this by generating an IAM policy based on an embedded base policy.
The default embedded IAM policy is sufficient for most use-cases.

This base policy can be found [here][service-account-policy-base].

You can disable the automatic creation of service accounts globally by setting the environment variable `MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT` to `False`.

You can also disable this on a per-bucket basis by setting `create_service_account: False` to the bucket definition in your `resources.yaml`.

## Examples

### `resources.yaml`

``` yaml
--8<-- "examples/my_group/resources.yaml"
```

[Source][example-resources-yaml]

---

[service-account-policy-base]: https://github.com/Alveel/minio-manager/blob/main/minio_manager/resources/policies.py
[example-resources-yaml]: https://github.com/Alveel/minio-manager/blob/main/examples/my_group/resources.yaml
