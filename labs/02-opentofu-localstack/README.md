# Lab 2: OpenTofu with LocalStack: S3 Bucket and Remote State

> Use OpenTofu against LocalStack to create an S3 state bucket, move a configuration to the S3 backend, and see state locking block a second run.

**Time:** about 30 minutes. **Level:** Intermediate.

## What you practise

- The "chicken and egg" problem of creating a state bucket
- Configuring the `s3` backend, including native S3 locking with `use_lockfile`
- Seeing what is stored in remote state and what a lock looks like
- The concepts in [terraform/03-state-and-backends.md](../../terraform/03-state-and-backends.md)

## Prerequisites

| Tool | Tested with | Notes |
| --- | --- | --- |
| Docker with Compose | Docker 29.1 | Runs LocalStack |
| OpenTofu | v1.12.2 | Needs 1.10 or later for `use_lockfile`. Terraform 1.10+ also works: replace `tofu` with `terraform`. |

**About the LocalStack image:** since LocalStack 2026.3.0, every image, including `latest`, needs a `LOCALSTACK_AUTH_TOKEN`. A free Hobby plan exists for non-commercial use. This lab pins `localstack/localstack:4.4.0`, which still starts without an account. To use a newer image, sign up, export `LOCALSTACK_AUTH_TOKEN`, change the image tag, and uncomment the token line in `docker-compose.yml`.

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Starts LocalStack on port 4566 with S3, STS, and IAM |
| `bootstrap/main.tf` | Creates the versioned state bucket `lab-tofu-state`, using local state |
| `app/backend.tf` | The S3 backend, pointing at LocalStack, with `use_lockfile = true` |
| `app/main.tf` | Creates a versioned bucket `lab-<environment>-artifacts` and one object |
| `.gitignore` | Keeps `.terraform/`, state files, and plans out of Git |

All credentials are the fake values `test` / `test` that LocalStack accepts. Never put real credentials in these files.

## Steps

### 1. Start LocalStack

```bash
docker compose up -d
curl -s localhost:4566/_localstack/health | grep -o '"s3": "[a-z]*"'
```

Wait until S3 shows `available` or `running`. The first start takes about a minute.

### 2. Create the state bucket

```bash
cd bootstrap
tofu init
tofu apply
```

Type `yes`. The output shows `state_bucket = "lab-tofu-state"`. This step keeps its own state in a local file, because the bucket cannot store state before it exists.

### 3. Deploy the app with remote state

```bash
cd ../app
tofu init
tofu apply
```

`tofu init` prints `Successfully configured the backend "s3"!`. After `apply`, check what LocalStack now holds:

```bash
docker exec localstack awslocal s3 ls
docker exec localstack awslocal s3 ls s3://lab-tofu-state --recursive
docker exec localstack awslocal s3 cp s3://lab-dev-artifacts/hello.txt -
```

### 4. See the state lock in action

Open two terminals in the `app` folder.

1. In terminal 1, run `tofu apply -var environment=qa` and **leave it waiting** at the `Enter a value:` prompt. OpenTofu holds the lock while it waits.
2. In terminal 2, list the state bucket, then try a plan:

```bash
docker exec localstack awslocal s3 ls s3://lab-tofu-state --recursive
tofu plan
```

3. Answer `no` in terminal 1. The lock is released, and `tofu plan` in terminal 2 now works.

<details><summary>What is happening?</summary>

With `use_lockfile = true`, OpenTofu writes `app/terraform.tfstate.tflock` next to the state file, using a conditional S3 write. A second run tries the same write, S3 rejects it with HTTP 412 (precondition failed), and OpenTofu reports `Error acquiring the state lock`. Before version 1.10 the usual way to lock was a DynamoDB table (`dynamodb_table`). That still works, but new setups should prefer `use_lockfile`.

</details>

## Expected result

```text
$ tofu apply                       # in app/
Outputs:
artifacts_bucket = "lab-dev-artifacts"

$ docker exec localstack awslocal s3 ls
2026-10-02 16:07:36 lab-tofu-state
2026-10-02 16:08:21 lab-dev-artifacts

$ docker exec localstack awslocal s3 ls s3://lab-tofu-state --recursive
2026-10-02 16:08:22       3298 app/terraform.tfstate

$ tofu plan                        # while another apply is waiting
│ Error: Error acquiring the state lock
│ Error message: operation error S3: PutObject, https response error
│ StatusCode: 412 ...
```

- The state file for `app/` lives in the S3 bucket, not on your disk.
- During step 4 a `terraform.tfstate.tflock` object appears, and the second run fails to get the lock.

Dates, sizes, and request IDs will be different on your machine.

## Clean up

```bash
cd app && tofu destroy
cd ../bootstrap && tofu destroy
cd .. && docker compose down
```

## Interview takeaways

- Remote state needs a bucket that exists before `init`. Create it with a separate bootstrap configuration, a script, or by hand.
- Always version the state bucket so you can recover an older state file.
- Locking stops two runs from writing state at the same time. Native S3 locking (`use_lockfile`) replaces the DynamoDB table in new setups.
- Related reading: [terraform/03-state-and-backends.md](../../terraform/03-state-and-backends.md) and [terraform/11-opentofu-vs-terraform.md](../../terraform/11-opentofu-vs-terraform.md).
