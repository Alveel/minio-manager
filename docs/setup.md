# Set up

An admin user should be used for these steps.

## Production Setup (KeePass Backend)

For production environments, use the secure KeePass backend:

## Steps

1. Create the bucket for the secret backend `minio-manager-secrets`

    `mc mb $ALIAS/minio-manager-secrets`

1. Create a user (either in MinIO or your identity provider)

    You can use `mc admin user add $ALIAS minio-manager` for a MinIO user

1. Create a policy that gives read/write access to the bucket for the secret backend

    You can use the example provided in the `examples` directory:

    `mc admin policy create $ALIAS minio-manager examples/minio-manager-secrets-policy.json`

1. Attach the policy to the user:

   - For MinIO: `mc admin policy attach $ALIAS minio-manager --user=minio-manager`
   - For LDAP: `mc idp ldap policy attach $ALIAS minio-manager --user='uid=minio-manager,cn=users,dc=your,dc=domain'`

1. Upload your secret backend (e.g. `secrets.kdbx`) to the bucket root
1. Create a MinIO service account/access key with either option:

   - `mc admin user svcacct add $ALIAS minio-manager` and note down the access and secret keys

1. Copy `.env.example` to `.env` and set the following variables to the obtained keys

   - `MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY`
   - `MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY`

1. Configure the other variables in the `.env` file. Descriptions of each variable can be found in the
   [Environment variables](#environment-variables) section

1. Each "bucket group" manager user must get its own policy.
   1. You can find an example in `examples/bucket-group-user-policy.json`
   1. `mc admin policy create $ALIAS infra-test-manager examples/bucket-group-user-policy.json`
   1. `mc idp ldap policy attach $ALIAS infra-test-manager --user='uid=infra-test-manager,cn=users,dc=your,dc=domain'`
1. You can then log in to the web console with this user to create an access key exactly like how we did it previously

## MinIO

At least two users are required in MinIO. One with access to a single bucket containing the secret backend, all other
users are to be used as "bucket group" managers. For each bucket created under this manager user a service account
(or access key in S3/MinIO terms) will be created.

### Secret manager

This is the controller user, that is able to authenticate to the secret backend, in order to retrieve the credentials to the service accounts

### Secret backend

We store our Keepass database inside a MinIO bucket. You can specify the name of this bucket by using the `MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET` variable.
The credentials for this bucket
In addition, you have to specify the password of this database with `MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY`, so that the controller user specified in `MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY` can access it.

We strongly suggest to pass these variables via masked and/or protected variables.

### Service Accounts



Also see [Service Account Details][service-account-details].

## Keepass

- The Keepass database's root group must be named "Passwords".
- You must have a group called "s3" and subgroups with the name of the MinIO cluster to be managed.
- Entry names must be unique.
- Entries are found by way of the title of the entry, the username is not considered when searching.

## Development Setup (YAML Backend)

For development and testing environments, you can use the simpler YAML secret backend:

### Quick Setup

```bash
# Start local MinIO test environment
make run-test-environment

# Configure controller user (creates YAML secrets file)
make configure-controller
```

This creates a local YAML secrets file at `tests/fixtures/testsecrets-insecure.yaml` with the controller user credentials.

### Manual YAML Backend Setup

1. **Set environment variables for YAML backend:**
   ```bash
   MINIO_MANAGER_SECRET_BACKEND_TYPE=yaml
   MINIO_MANAGER_SECRET_BACKEND_PATH=path/to/secrets.yaml
   ```

2. **Create initial secrets file:**
   ```yaml
   # secrets.yaml
   controller-user-name:
     access_key: "your-controller-access-key"
     secret_key: "your-controller-secret-key"
   ```

3. **Service account credentials are automatically managed** - MinIO Manager will add/update service account entries as needed.

### YAML Backend Features

- **Human-readable format** for easy debugging
- **Automatic credential management** for service accounts
- **No encryption** (suitable for development only)
- **Local file storage** (no S3 bucket required)
- **Session cleanup** in test environments

**⚠️ Security Warning:** YAML backend stores credentials in plain text. Only use for development and testing environments.

## Configuration variables

See [Configuration environment variables][environment-variables]
