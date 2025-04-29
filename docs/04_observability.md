# Langfuse Observability

You can configure your own hosted Langfuse instance for observability

  Flags

   * `--url` / `-u`         is URL of the langfuse instance (required if not specified in `--config-file`)
   * `--project-id` / `-p`  is the langfuse project id (required if not specified in `--config-file`)
   * `--api-key`            is the langfuse api key (required if not specified in `--config-file`)
   * `--health-uri`         is the Health URI of the langfuse instance (required if not specified in `--config-file`)
   * `--config-file`        is a config file for the langfuse integration (can be fetched using orchestrate settings )
   * `--config-json`        is config json object for the langfuse integration, this object should contain you Langfuse`public_key`

```bash
orchestrate settings observability langfuse configure \
 --url "https://cloud.langfuse.com//api/public/otel" \
 --project-id default \
 --api-key "sk-lf-0000-0000-0000-0000-0000" \
 --health-uri "https://cloud.langfuse.com" \
 --config-json '{"public_key": "pk-lf-0000-0000-0000-0000-0000"}'
 ```

`orchestrate settings observability langfuse configure --config-file=path_to_file.yml`

   ```yaml
spec_version: v1
kind: langfuse
project_id: default
api_key: sk-lf-00000-00000-00000-00000-00000
url: https://cloud.langfuse.com//api/public/otel
host_health_uri: https://cloud.langfuse.com
config_json: 
  public_key: pk-lf-00000-00000-00000-00000-00000
mask_pii: true
   ```