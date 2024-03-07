# Configuration

## Environment variables

Required variables without a default value must be manually configured.

| **Variable**                                      | **Description**                                                                                  | **Required** | **Default**                        |
|---------------------------------------------------|--------------------------------------------------------------------------------------------------|--------------|------------------------------------|
| `MINIO_MANAGER_CLUSTER_NAME`                      | The name of the cluster, used to query the secret backend                                        | Yes          |                                    |
| `MINIO_MANAGER_S3_ENDPOINT`¹                      | What host:port to use as MinIO/S3 endpoint                                                       | Yes          |                                    |
| `MINIO_MANAGER_MINIO_CONTROLLER_USER`             | The name of the entry in the secret backend for the controller user                              | Yes          |                                    |
| `MINIO_MANAGER_SECRET_BACKEND_TYPE`²              | What secret backend to use                                                                       | Yes          |                                    |
| `MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY`      | The access key to the S3 bucket where the secret database is stored                              | Yes          |                                    |
| `MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY`      | The secret key to the S3 bucket where the secret database is stored                              | Yes          |                                    |
| `MINIO_MANAGER_KEEPASS_PASSWORD`                  | Keepass database password                                                                        | With Keepass |                                    |
| `MINIO_MANAGER_KEEPASS_FILE`                      | he name of the database file in the S3 bucket                                                    | Yes          | `secrets.kdbx`                     |
| `MINIO_MANAGER_CLUSTER_RESOURCES_FILE`            | The YAML file with the MinIO resource configuration (buckets, policies, etc.)                    | Yes          | `resources.yaml`                   |
| `MINIO_MANAGER_MINIO_ENDPOINT_SECURE`             | Whether to use HTTPS for the endpoint                                                            | Yes          | `True`                             |
| `MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET`          | The name of the bucket where the secret backend is kept                                          | Yes          | `minio-manager-secrets`            |
| `MINIO_MANAGER_LOG_LEVEL`³                        | The log level of the application.                                                                | No           | `INFO`                             |
| `MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING`         | Whether to globally enable (`Enabled`) or suspend (`Suspended`) bucket versioning                | Yes          | `Suspended`                        |
| `MINIO_MANAGER_DEFAULT_LIFECYCLE_POLICY`          | What lifecycle policy (in `mc ilm export` format) to attach to all buckets by default            | No           |                                    |
| `MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT`       | Whether to automatically create service accounts for each bucket with access to just that bucket | No           | `True`                             |
| `MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_BASE_FILE`⁴ | What policy to use as a base for a service account when automatically generated                  | No           | `service-account-policy-base.json` |
| `MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES`           | Comma-separated list of prefixes of bucket names this controller user is allowed to manage       | No           | `""`                               |

1. Only specify the host and port as per the [example `.env`](#configenv), without `https://` or trailing slashes
2. Currently only Keepass is supported
3. Possible values are `INFO` or `DEBUG`
4. Defaults to [`service-account-policy-base.json`][service-account-policy-base]. MUST contain `BUCKET_NAME_REPLACE_ME` in the resources to work

## Examples

### `config.env`

``` shell
--8<-- "examples/my_group/.env"
```

[Source][example-config-env]

### `resources.yaml`

``` yaml
--8<-- "examples/my_group/resources.yaml"
```

[Source][example-resources-yaml]

### Service account policy base file

``` json
--8<-- "examples/my_service_account_policy.json"
```

[Source][service-account-policy-base]

---

[example-config-env]: https://github.com/Alveel/minio-manager/blob/main/examples/my_group/.env
[example-resources-yaml]: https://github.com/Alveel/minio-manager/blob/main/examples/my_group/resources.yaml
[service-account-policy-base]: https://github.com/Alveel/minio-manager/blob/main/minio_manager/resources/service-account-policy-base.json
