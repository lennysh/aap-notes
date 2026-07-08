#!/usr/bin/env python3
"""Generate AAP 2.6 annotated inventory and vars-example files from the variable catalog."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "AAP26" / "containerized"

# fmt: (name, comment, example_value)
# example_value=None means document-only (complex type or path/secret placeholder)

def section(title: str, doc_url: str | None = None) -> list[tuple[str, str, str | None]]:
    return [("__SECTION__", title, doc_url)]


CATALOG: list[tuple[str, str, str | None]] = [
    *section("Common / installer-wide"),
    ("bundle_dir", "Directory containing offline bundle (images/ and collections/); required when bundle_install=true", "/path/to/bundle"),
    ("bundle_install", "Use offline/bundled installation instead of pulling from registry", "false"),
    ("ca_tls_cert", "Path to custom TLS CA certificate used to sign component certificates", "/path/to/ca.crt"),
    ("ca_tls_key", "Path to custom TLS CA private key", "/path/to/ca.key"),
    ("ca_tls_key_passphrase", "Passphrase for the TLS CA private key, if encrypted", "<set your own>"),
    ("ca_tls_remote", "TLS CA cert/key files live on remote hosts (not the Ansible control node)", "false"),
    ("client_request_timeout", "End-user HTTP request timeout in seconds (minimum 10); drives nginx/uwsgi/gunicorn timeouts", "30"),
    ("container_compress", "Compression algorithm for container layers (e.g. gzip)", "gzip"),
    ("container_keep_images", "Keep container images on hosts during uninstall", "false"),
    ("container_pull_images", "Pull newer container images from registry during install/upgrade", "true"),
    ("custom_ca_cert", "Org CA PEM added to the AAP platform trust bundle for outbound TLS to external services (CyberArk, corporate DBs, APIs); required for *_pg_cert_auth with verify-ca/verify-full; not automatic in Execution Environments", "/path/to/custom-ca.crt"),
    ("feature_flags", "Dictionary of feature flags (keys must start with feature_, values boolean); use vars.yml", None),
    ("images_tmp_dir", "Directory to extract bundled container images during offline install", "/tmp"),
    ("registry_auth", "Authenticate to the container registry (disable for open registries)", "true"),
    ("registry_ns_aap", "Registry namespace for AAP component images", "ansible-automation-platform-26"),
    ("registry_ns_aap_tp", "Registry namespace for AAP tech-preview images", "ansible-automation-platform-tech-preview"),
    ("registry_ns_rhel", "Registry namespace for RHEL base images", "rhel9"),
    ("registry_tls_verify", "Verify TLS when connecting to the container registry", "true"),
    ("registry_url", "Container registry URL", "registry.redhat.io"),
    ("use_archive_compression", "Compress backup archive files globally (overridden per-component vars exist)", "true"),
    ("use_db_compression", "Compress database dumps globally during backup", "false"),

    *section("Host tuning"),
    ("tune_host_limits", "Apply kernel sysctl, ulimit, and podman PID tuning on service hosts during install", "true"),
    ("host_tuning_sysctl_fs_inotify_max_user_instances", "sysctl fs.inotify.max_user_instances written to /etc/sysctl.d/99-aap.conf", "8192"),
    ("host_tuning_sysctl_fs_inotify_max_user_watches", "sysctl fs.inotify.max_user_watches written to /etc/sysctl.d/99-aap.conf", "524288"),
    ("host_tuning_nofile_limit_soft", "Soft nofile ulimit for the user running AAP containers", "524288"),
    ("host_tuning_nofile_limit_hard", "Hard nofile ulimit for the user running AAP containers", "524288"),

    *section("Container images"),
    ("automationmetrics_image", "Automation Metrics Service container image tag", "metrics-service-rhel9:latest"),
    ("controller_image", "Automation Controller container image tag", "controller-rhel9:latest"),
    ("de_extra_images", "Additional Decision Environment images to upload to Hub; list — use vars.yml", None),
    ("de_supported_image", "Default Decision Environment supported image tag", "de-supported-rhel9:latest"),
    ("eda_image", "Automation EDA Controller API container image tag", "eda-controller-rhel9:latest"),
    ("eda_web_image", "Automation EDA Controller UI container image tag", "eda-controller-ui-rhel9:latest"),
    ("ee_extra_images", "Additional Execution Environment images to upload to Hub; list — use vars.yml", None),
    ("ee_minimal_image", "Minimal Execution Environment image tag", "ee-minimal-rhel9:latest"),
    ("ee_supported_image", "Default Execution Environment supported image tag", "ee-supported-rhel9:latest"),
    ("gateway_image", "Automation Gateway container image tag", "gateway-rhel9:latest"),
    ("gateway_proxy_image", "Automation Gateway proxy (Envoy) container image tag", "gateway-proxy-rhel9:latest"),
    ("hub_image", "Automation Hub API container image tag", "hub-rhel9:latest"),
    ("hub_web_image", "Automation Hub UI container image tag", "hub-web-rhel9:latest"),
    ("lightspeed_image", "Ansible Lightspeed container image tag", "lightspeed-rhel9:latest"),
    ("lightspeed_chatbot_image", "Ansible Lightspeed chatbot container image tag", "lightspeed-chatbot-rhel9:latest"),
    ("mcp_image", "Ansible MCP Server container image tag", "mcp-server-rhel9:latest"),
    ("mcp_tools_image", "Ansible Lightspeed MCP tools sidecar image tag", "mcp-tools-rhel9:latest"),
    ("pcp_image", "Performance Co-Pilot container image tag", "pcp:latest"),
    ("postgresql_image", "PostgreSQL container image tag (managed database topology)", "postgresql-15:latest"),
    ("receptor_image", "Receptor container image tag", "receptor-rhel9:latest"),
    ("redis_image", "Redis container image tag", "redis-6:latest"),

    *section("PostgreSQL / managed database"),
    ("postgresql_admin_database", "PostgreSQL admin database name for managed [database] hosts", "postgres"),
    ("postgresql_disable_tls", "Disable TLS on the managed PostgreSQL container", "false"),
    ("postgresql_effective_cache_size", "PostgreSQL effective_cache_size tuning parameter", "4GB"),
    ("postgresql_extra_settings", "Extra postgresql.conf settings as list of setting/value dicts; use vars.yml", None),
    ("postgresql_keep_databases", "Keep databases during uninstall (also: postgresql_keep_databases via -e on uninstall)", "false"),
    ("postgresql_log_destination", "PostgreSQL log destination", "/dev/stderr"),
    ("postgresql_max_connections", "PostgreSQL max_connections", "1024"),
    ("postgresql_password_encryption", "PostgreSQL password_encryption method", "scram-sha-256"),
    ("postgresql_port", "PostgreSQL TCP port for managed database and external connections", "5432"),
    ("postgresql_shared_buffers", "PostgreSQL shared_buffers tuning parameter", "1GB"),
    ("postgresql_tls_cert", "TLS certificate for managed PostgreSQL", "/path/to/postgresql.crt"),
    ("postgresql_tls_key", "TLS private key for managed PostgreSQL", "/path/to/postgresql.key"),
    ("postgresql_tls_remote", "PostgreSQL TLS files are on remote hosts, not the control node", "false"),
    ("postgresql_use_archive_compression", "Compress PostgreSQL backup archives", "true"),

    *section("Redis"),
    ("redis_cluster_ip", "Bind IP for Redis cluster nodes (cluster mode)", "10.0.0.1"),
    ("redis_disable_tls", "Disable TLS for Redis cluster TCP connections", "false"),
    ("redis_mode", "Redis topology: cluster (default enterprise) or standalone (growth/single-node)", "cluster"),
    ("redis_port", "Redis TCP port", "6379"),
    ("redis_prefer_ipv6", "Prefer IPv6 addresses in dual-stack Redis cluster setups", "false"),
    ("redis_tls_cert", "TLS certificate for Redis cluster", "/path/to/redis.crt"),
    ("redis_tls_key", "TLS private key for Redis cluster", "/path/to/redis.key"),
    ("redis_tls_remote", "Redis TLS files are on remote hosts", "false"),
    ("redis_use_archive_compression", "Compress Redis backup archives", "true"),

    *section("Receptor"),
    ("receptor_disable_signing", "Disable Receptor work signing", "false"),
    ("receptor_disable_tls", "Disable Receptor mesh TLS", "false"),
    ("receptor_log_level", "Receptor log level (debug, info, warning, error)", "info"),
    ("receptor_mintls13", "Require TLS 1.3 minimum for Receptor connections", "false"),
    ("receptor_peers", "Additional Receptor peer definitions; list — use vars.yml", None),
    ("receptor_port", "Receptor mesh listening port", "27199"),
    ("receptor_protocol", "Receptor mesh protocol (tcp or udp); can also be set per-host", "tcp"),
    ("receptor_signing_private_key", "Receptor work signing private key path", "/path/to/signing.key"),
    ("receptor_signing_public_key", "Receptor work signing public key path", "/path/to/signing.pub"),
    ("receptor_signing_remote", "Receptor signing keys are on remote hosts", "false"),
    ("receptor_tls_cert", "Receptor TLS certificate path", "/path/to/receptor.crt"),
    ("receptor_tls_key", "Receptor TLS private key path", "/path/to/receptor.key"),
    ("receptor_tls_remote", "Receptor TLS files are on remote hosts", "false"),
    ("receptor_use_archive_compression", "Compress Receptor backup archives", "true"),

    *section("Performance Co-Pilot monitoring"),
    ("setup_monitoring", "Install Performance Co-Pilot (PCP) on control-plane nodes", "false"),
    ("pcp_pmcd_port", "PCP pmcd listening port", "44321"),
    ("pcp_pmproxy_port", "PCP pmproxy listening port", "44322"),
    ("pcp_firewall_zone", "firewalld zone for PCP services", "public"),
    ("pcp_use_archive_compression", "Compress PCP backup archives", "true"),

    *section("Log gathering (ansible.containerized_installer.log_gathering playbook)"),
    ("case_number", "Red Hat support case number included in sos report", "00000000"),
    ("clean", "Obfuscate sensitive data in sos report output", "false"),
    ("upload", "Automatically upload sos report to Red Hat", "false"),
    ("target_sos_directory", "Directory where sos report files are written", "/tmp"),
]

GATEWAY_VARS = [
    *section("AAP Gateway", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#platform-gateway-variables"),
    ("gateway_admin_user", "Automation Gateway admin username", "admin"),
    ("gateway_extra_settings", "Extra Gateway Django settings as list of setting/value dicts; use vars.yml", None),
    ("gateway_main_url", "Public URL users reach for the Gateway (must include http:// or https://)", "https://aap.example.org"),
    ("gateway_nginx_client_max_body_size", "Gateway nginx client_max_body_size", "5m"),
    ("gateway_nginx_disable_hsts", "Disable HTTP Strict Transport Security on Gateway nginx", "false"),
    ("gateway_nginx_disable_https", "Serve Gateway over HTTP only (disable HTTPS)", "false"),
    ("gateway_nginx_hsts_max_age", "Gateway HSTS max-age header value in seconds", "63072000"),
    ("gateway_nginx_http_port", "Gateway nginx HTTP port (host mapped)", "8083"),
    ("gateway_nginx_https_port", "Gateway nginx HTTPS port (host mapped)", "8446"),
    ("gateway_nginx_https_protocols", "Gateway nginx SSL protocols; list — use vars.yml", None),
    ("gateway_nginx_user_headers", "Custom nginx headers; list — use vars.yml", None),
    ("gateway_nginx_read_timeout", "Gateway nginx proxy read timeout seconds (default derived from client_request_timeout)", "15"),
    ("gateway_pg_cert_auth", "Use certificate authentication for Gateway PostgreSQL connection", "false"),
    ("gateway_pg_port", "Gateway PostgreSQL port", "5432"),
    ("gateway_pg_sslmode", "Gateway PostgreSQL sslmode (disable, allow, prefer, require, verify-ca, verify-full)", "prefer"),
    ("gateway_pg_tls_cert", "Client TLS certificate for Gateway PostgreSQL connection", "/path/to/gateway-db.crt"),
    ("gateway_pg_tls_key", "Client TLS key for Gateway PostgreSQL connection", "/path/to/gateway-db.key"),
    ("gateway_pg_username", "Gateway PostgreSQL username", "gateway"),
    ("gateway_redis_disable_tls", "Disable TLS for external Redis used by Gateway", "false"),
    ("gateway_redis_host", "External Redis hostname for Gateway (multi-node / non-socket setups)", "redis.example.org"),
    ("gateway_redis_password", "External Redis password for Gateway", "<set your own>"),
    ("gateway_redis_port", "External Redis port for Gateway", "6379"),
    ("gateway_redis_tls_cert", "TLS client certificate for Gateway Redis connection", "/path/to/gateway-redis.crt"),
    ("gateway_redis_tls_key", "TLS client key for Gateway Redis connection", "/path/to/gateway-redis.key"),
    ("gateway_redis_username", "External Redis username for Gateway", "gateway"),
    ("gateway_secret_key", "Django secret key for Gateway (auto-generated if unset)", "<set your own>"),
    ("gateway_tls_cert", "Gateway TLS certificate (PEM path on control node or remote per gateway_tls_remote)", "/path/to/gateway.crt"),
    ("gateway_tls_key", "Gateway TLS private key", "/path/to/gateway.key"),
    ("gateway_tls_remote", "Gateway TLS cert/key files are on the Gateway host, not the control node", "false"),
    ("gateway_grpc_server_processes", "Gateway auth gRPC server worker processes", "5"),
    ("gateway_grpc_server_max_threads_per_process", "Gateway auth gRPC max threads per process", "10"),
    ("gateway_grpc_auth_service_timeout", "Gateway auth gRPC service timeout (e.g. 15s)", "15s"),
    ("gateway_uwsgi_listen_queue_size", "Gateway uwsgi listen queue size", "4096"),
    ("gateway_use_archive_compression", "Compress Gateway backup archives", "true"),
    ("gateway_use_db_compression", "Compress Gateway database dumps during backup", "false"),
    ("gateway_uwsgi_processes", "Gateway uwsgi worker processes (default: 2 * CPU + 1)", "5"),
    ("gateway_uwsgi_timeout", "Gateway uwsgi harakiri timeout seconds", "10"),
    ("gateway_uwsgi_timeout_grace_period", "Gateway uwsgi harakiri grace period seconds", "2"),
    ("gateway_jwt_expiration_buffer_in_seconds", "JWT expiration buffer passed to Gateway auth service", "15"),
]

CONTROLLER_VARS = [
    *section("AAP Controller", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#controller-variables"),
    ("controller_admin_user", "Automation Controller admin username", "admin"),
    ("controller_create_preload_data", "Load default job templates and other preload data on first install", "true"),
    ("controller_event_workers", "Number of Controller event worker processes", "4"),
    ("controller_extra_settings", "Extra Controller settings as list of setting/value dicts; use vars.yml", None),
    ("controller_license_file", "Path to Controller license file on the Ansible control node", "/path/to/license.json"),
    ("controller_nginx_client_max_body_size", "Controller nginx client_max_body_size", "5m"),
    ("controller_nginx_disable_hsts", "Disable HSTS on Controller nginx", "false"),
    ("controller_nginx_disable_https", "Serve Controller over HTTP only", "false"),
    ("controller_nginx_hsts_max_age", "Controller HSTS max-age in seconds", "63072000"),
    ("controller_nginx_http_port", "Controller nginx HTTP port", "8080"),
    ("controller_nginx_https_port", "Controller nginx HTTPS port", "8443"),
    ("controller_nginx_https_protocols", "Controller nginx SSL protocols; list — use vars.yml", None),
    ("controller_nginx_user_headers", "Custom Controller nginx headers; list — use vars.yml", None),
    ("controller_nginx_read_timeout", "Controller nginx proxy read timeout seconds", "15"),
    ("controller_percent_memory_capacity", "Fraction of host memory allocated to Controller task capacity (0.0–1.0)", "1.0"),
    ("controller_pg_cert_auth", "Use certificate authentication for Controller PostgreSQL", "false"),
    ("controller_pg_port", "Controller PostgreSQL port", "5432"),
    ("controller_pg_socket", "PostgreSQL unix socket directory (instead of TCP host) for Controller DB", "/var/run/postgresql"),
    ("controller_pg_sslmode", "Controller PostgreSQL sslmode", "prefer"),
    ("controller_pg_tls_cert", "Client TLS certificate for Controller PostgreSQL", "/path/to/controller-db.crt"),
    ("controller_pg_tls_key", "Client TLS key for Controller PostgreSQL", "/path/to/controller-db.key"),
    ("controller_pg_username", "Controller PostgreSQL username", "awx"),
    ("controller_postinstall", "Run Controller postinstall to create projects, users, roles, etc.", "false"),
    ("controller_postinstall_async_delay", "Seconds between Controller postinstall retries", "1"),
    ("controller_postinstall_async_retries", "Maximum Controller postinstall retry attempts", "30"),
    ("controller_postinstall_dir", "Local directory containing Controller postinstall playbooks/config", "/path/to/postinstall"),
    ("controller_postinstall_ignore_files", "Files to skip during Controller postinstall; list — use vars.yml", None),
    ("controller_postinstall_repo_ref", "Git ref (branch/tag) for Controller postinstall repository", "main"),
    ("controller_postinstall_repo_url", "Git URL for Controller postinstall repository (may include credentials)", "https://github.org/org/postinstall.git"),
    ("controller_secret_key", "Controller secret key (auto-generated if unset)", "<set your own>"),
    ("controller_tls_cert", "Controller TLS certificate path", "/path/to/controller.crt"),
    ("controller_tls_key", "Controller TLS private key path", "/path/to/controller.key"),
    ("controller_tls_remote", "Controller TLS files are on the Controller host", "false"),
    ("controller_uwsgi_listen_queue_size", "Controller uwsgi listen queue size", "2048"),
    ("controller_use_archive_compression", "Compress Controller backup archives", "true"),
    ("controller_use_db_compression", "Compress Controller database dumps during backup", "false"),
    ("controller_uwsgi_processes", "Controller uwsgi worker processes (default: 2 * CPU + 1)", "5"),
    ("controller_uwsgi_timeout", "Controller uwsgi harakiri timeout seconds", "10"),
    ("metrics_utility_cronjob_gather_schedule", "Metrics Utility gather cron schedule (systemd calendar format)", "*-*-* *:00:00"),
    ("metrics_utility_cronjob_report_schedule", "Metrics Utility report cron schedule (systemd calendar format)", "*-*-02 00:00:00"),
    ("metrics_utility_enabled", "Enable Metrics Utility integration in Controller", "false"),
    ("metrics_utility_extra_settings", "Metrics Utility extra settings; list — use vars.yml", None),
]

HUB_VARS = [
    *section("AAP Automation Hub", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#hub-variables"),
    ("hub_extra_settings", "Extra Hub settings as list of setting/value dicts; use vars.yml", None),
    ("hub_data_path_exclude", "Paths excluded from Hub backup; list — use vars.yml", None),
    ("hub_galaxy_importer", "Galaxy importer configuration dictionary; use vars.yml", None),
    ("hub_main_url", "Public Hub URL (must include http:// or https://); used for redirects and TLS SANs", "https://hub.example.org"),
    ("hub_nginx_client_max_body_size", "Hub nginx client_max_body_size", "20m"),
    ("hub_nginx_disable_hsts", "Disable HSTS on Hub nginx", "false"),
    ("hub_nginx_disable_https", "Serve Hub over HTTP only", "false"),
    ("hub_nginx_hsts_max_age", "Hub HSTS max-age in seconds", "63072000"),
    ("hub_nginx_http_port", "Hub nginx HTTP port", "8081"),
    ("hub_nginx_https_port", "Hub nginx HTTPS port", "8444"),
    ("hub_nginx_https_protocols", "Hub nginx SSL protocols; list — use vars.yml", None),
    ("hub_nginx_user_headers", "Custom Hub nginx headers; list — use vars.yml", None),
    ("hub_nginx_read_timeout", "Hub nginx proxy read timeout seconds", "15"),
    ("hub_pg_cert_auth", "Use certificate authentication for Hub PostgreSQL", "false"),
    ("hub_pg_port", "Hub PostgreSQL port", "5432"),
    ("hub_pg_socket", "PostgreSQL unix socket directory for Hub DB", "/var/run/postgresql"),
    ("hub_pg_sslmode", "Hub PostgreSQL sslmode", "prefer"),
    ("hub_pg_tls_cert", "Client TLS certificate for Hub PostgreSQL", "/path/to/hub-db.crt"),
    ("hub_pg_tls_key", "Client TLS key for Hub PostgreSQL", "/path/to/hub-db.key"),
    ("hub_pg_username", "Hub PostgreSQL username", "pulp"),
    ("hub_postinstall", "Run Hub postinstall to create collections, users, groups, etc.", "false"),
    ("hub_postinstall_async_delay", "Seconds between Hub postinstall retries", "1"),
    ("hub_postinstall_async_retries", "Maximum Hub postinstall retry attempts", "30"),
    ("hub_postinstall_dir", "Local directory containing Hub postinstall playbooks/config", "/path/to/hub-postinstall"),
    ("hub_postinstall_ignore_files", "Files to skip during Hub postinstall; list — use vars.yml", None),
    ("hub_postinstall_repo_ref", "Git ref for Hub postinstall repository", "main"),
    ("hub_postinstall_repo_url", "Git URL for Hub postinstall repository", "https://github.org/org/hub-postinstall.git"),
    ("hub_secret_key", "Hub secret key (auto-generated if unset)", "<set your own>"),
    ("hub_seed_collections", "Upload bundled Ansible collections to Hub during install (requires bundle_install)", "true"),
    ("hub_storage_backend", "Hub content storage backend: file, azure, or s3", "file"),
    ("hub_tls_cert", "Hub TLS certificate path", "/path/to/hub.crt"),
    ("hub_tls_key", "Hub TLS private key path", "/path/to/hub.key"),
    ("hub_tls_remote", "Hub TLS files are on the Hub host", "false"),
    ("hub_workers", "Hub content worker process count", "2"),
    ("hub_use_archive_compression", "Compress Hub backup archives", "true"),
    ("hub_use_db_compression", "Compress Hub database dumps during backup", "false"),
    ("hub_api_workers", "Hub API gunicorn workers (default: 2 * CPU + 1)", "5"),
    ("hub_gunicorn_timeout", "Hub API/content gunicorn timeout seconds", "10"),
    ("hub_gunicorn_timeout_grace_period", "Hub gunicorn graceful timeout seconds", "2"),
    *section("Automation Hub — shared NFS storage (required for multi-node file backend)"),
    ("hub_shared_data_path", "NFS export in host:dir format with read-write access for Hub data", "nfs.example.org:/export/hub"),
    ("hub_shared_data_mount_opts", "Mount options for Hub NFS share", "rw,sync,hard"),
    *section("Automation Hub — Azure blob storage (set hub_storage_backend=azure)"),
    ("hub_azure_account_key", "Azure storage account key", "<set your own>"),
    ("hub_azure_account_name", "Azure storage account name", "mystorageaccount"),
    ("hub_azure_container", "Azure blob container name", "pulp"),
    ("hub_azure_extra_settings", "Extra Azure storage settings dictionary; use vars.yml", None),
    *section("Automation Hub — S3 storage (set hub_storage_backend=s3)"),
    ("hub_s3_access_key", "AWS S3 access key ID", "<set your own>"),
    ("hub_s3_secret_key", "AWS S3 secret access key", "<set your own>"),
    ("hub_s3_bucket_name", "AWS S3 bucket name", "pulp"),
    ("hub_s3_extra_settings", "Extra S3 storage settings dictionary; use vars.yml", None),
    *section("Automation Hub — content signing"),
    ("hub_collection_auto_sign", "Automatically sign imported collections when collection signing is enabled", "false"),
    ("hub_collection_signing", "Enable GPG signing for Ansible collections in Hub", "false"),
    ("hub_collection_signing_key", "GPG private key path for collection signing", "/path/to/collection-signing.key"),
    ("hub_collection_signing_pass", "Passphrase for collection signing GPG key", "<set your own>"),
    ("hub_collection_signing_service", "Hub signing service name for collections", "ansible-default"),
    ("hub_container_signing", "Enable GPG signing for container images in Hub", "false"),
    ("hub_container_signing_key", "GPG private key path for container signing", "/path/to/container-signing.key"),
    ("hub_container_signing_pass", "Passphrase for container signing GPG key", "<set your own>"),
    ("hub_container_signing_service", "Hub signing service name for containers", "container-default"),
]

EDA_VARS = [
    *section("AAP EDA Controller", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#event-driven-ansible-variables"),
    ("eda_activation_workers", "Number of EDA activation worker processes", "2"),
    ("eda_debug", "Enable EDA debug mode", "false"),
    ("eda_extra_settings", "Extra EDA settings as list of setting/value dicts; use vars.yml", None),
    ("eda_nginx_client_max_body_size", "EDA nginx client_max_body_size", "1m"),
    ("eda_nginx_disable_hsts", "Disable HSTS on EDA nginx", "false"),
    ("eda_nginx_disable_https", "Serve EDA over HTTP only", "false"),
    ("eda_nginx_hsts_max_age", "EDA HSTS max-age in seconds", "63072000"),
    ("eda_nginx_http_port", "EDA nginx HTTP port", "8082"),
    ("eda_nginx_https_port", "EDA nginx HTTPS port", "8445"),
    ("eda_nginx_https_protocols", "EDA nginx SSL protocols; list — use vars.yml", None),
    ("eda_nginx_user_headers", "Custom EDA nginx headers; list — use vars.yml", None),
    ("eda_nginx_read_timeout", "EDA nginx proxy read timeout seconds", "15"),
    ("eda_pg_cert_auth", "Use certificate authentication for EDA PostgreSQL", "false"),
    ("eda_pg_port", "EDA PostgreSQL port", "5432"),
    ("eda_pg_socket", "PostgreSQL unix socket directory for EDA DB", "/var/run/postgresql"),
    ("eda_pg_sslmode", "EDA PostgreSQL sslmode", "prefer"),
    ("eda_pg_tls_cert", "Client TLS certificate for EDA PostgreSQL", "/path/to/eda-db.crt"),
    ("eda_pg_tls_key", "Client TLS key for EDA PostgreSQL", "/path/to/eda-db.key"),
    ("eda_pg_username", "EDA PostgreSQL username", "eda"),
    ("eda_redis_disable_tls", "Disable TLS for external Redis used by EDA (multi-node setups)", "false"),
    ("eda_redis_host", "External Redis hostname for EDA", "redis.example.org"),
    ("eda_redis_password", "External Redis password for EDA", "<set your own>"),
    ("eda_redis_port", "External Redis port for EDA", "6379"),
    ("eda_redis_tls_cert", "TLS client certificate for EDA Redis connection", "/path/to/eda-redis.crt"),
    ("eda_redis_tls_key", "TLS client key for EDA Redis connection", "/path/to/eda-redis.key"),
    ("eda_redis_username", "External Redis username for EDA", "eda"),
    ("eda_safe_plugins", "Allowlisted EDA rulebook plugins; list — use vars.yml", None),
    ("eda_secret_key", "EDA secret key (auto-generated if unset)", "<set your own>"),
    ("eda_tls_cert", "EDA TLS certificate path", "/path/to/eda.crt"),
    ("eda_tls_key", "EDA TLS private key path", "/path/to/eda.key"),
    ("eda_tls_remote", "EDA TLS files are on the EDA host", "false"),
    ("eda_type", "EDA node role: hybrid, api, worker, or event-stream (can be set per-host in [automationeda])", "hybrid"),
    ("eda_event_stream_prefix_path", "Gateway proxy path prefix for webhook event streams", "/eda-event-streams"),
    ("eda_event_stream_url", "Public URL for EDA webhook event streams (via Gateway proxy)", "https://aap.example.org/eda-event-streams"),
    ("eda_event_stream_mtls", "Enable mTLS for EDA event stream endpoints", "true"),
    ("eda_event_stream_mtls_prefix_path", "Gateway proxy path prefix for mTLS event streams", "/mtls/eda-event-streams"),
    ("eda_event_stream_mtls_url", "Public mTLS URL for EDA event streams", "https://aap.example.org/mtls/eda-event-streams"),
    ("eda_workers", "Number of EDA worker processes", "2"),
    ("eda_use_archive_compression", "Compress EDA backup archives", "true"),
    ("eda_use_db_compression", "Compress EDA database dumps during backup", "false"),
    ("eda_gunicorn_workers", "EDA gunicorn workers (default: 2 * CPU + 1)", "5"),
    ("eda_gunicorn_timeout", "EDA gunicorn timeout seconds", "10"),
    ("eda_gunicorn_timeout_grace_period", "EDA gunicorn graceful timeout seconds", "2"),
]

LIGHTSPEED_VARS = [
    *section("AAP Lightspeed", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#lightspeed-variables"),
    ("lightspeed_admin_user", "Ansible Lightspeed admin username", "admin"),
    ("lightspeed_chat_rate_throttle", "Rate limit for Lightspeed chat requests", "10/minute"),
    ("lightspeed_nginx_client_max_body_size", "Lightspeed nginx client_max_body_size", "5m"),
    ("lightspeed_nginx_disable_hsts", "Disable HSTS on Lightspeed nginx", "false"),
    ("lightspeed_nginx_disable_https", "Serve Lightspeed over HTTP only", "false"),
    ("lightspeed_nginx_hsts_max_age", "Lightspeed HSTS max-age in seconds", "63072000"),
    ("lightspeed_nginx_http_port", "Lightspeed nginx HTTP port", "8084"),
    ("lightspeed_nginx_https_port", "Lightspeed nginx HTTPS port", "8447"),
    ("lightspeed_nginx_https_protocols", "Lightspeed nginx SSL protocols; list — use vars.yml", None),
    ("lightspeed_nginx_user_headers", "Custom Lightspeed nginx headers; list — use vars.yml", None),
    ("lightspeed_nginx_read_timeout", "Lightspeed nginx proxy read timeout seconds", "15"),
    ("lightspeed_pg_cert_auth", "Use certificate authentication for Lightspeed PostgreSQL", "false"),
    ("lightspeed_pg_port", "Lightspeed PostgreSQL port", "5432"),
    ("lightspeed_pg_sslmode", "Lightspeed PostgreSQL sslmode", "prefer"),
    ("lightspeed_pg_tls_cert", "Client TLS certificate for Lightspeed PostgreSQL", "/path/to/lightspeed-db.crt"),
    ("lightspeed_pg_tls_key", "Client TLS key for Lightspeed PostgreSQL", "/path/to/lightspeed-db.key"),
    ("lightspeed_pg_username", "Lightspeed PostgreSQL username", "lightspeed"),
    ("lightspeed_secret_key", "Lightspeed secret key (auto-generated if unset)", "<set your own>"),
    ("lightspeed_tls_cert", "Lightspeed TLS certificate path", "/path/to/lightspeed.crt"),
    ("lightspeed_tls_key", "Lightspeed TLS private key path", "/path/to/lightspeed.key"),
    ("lightspeed_tls_remote", "Lightspeed TLS files are on the Lightspeed host", "false"),
    ("lightspeed_use_archive_compression", "Compress Lightspeed backup archives", "true"),
    ("lightspeed_use_db_compression", "Compress Lightspeed database dumps during backup", "false"),
    ("lightspeed_uwsgi_listen_queue_size", "Lightspeed uwsgi listen queue size", "2048"),
    ("lightspeed_uwsgi_processes", "Lightspeed uwsgi workers (default: 2 * CPU + 1)", "5"),
    ("lightspeed_uwsgi_timeout", "Lightspeed uwsgi harakiri timeout seconds", "60"),
    ("lightspeed_uwsgi_timeout_grace_period", "Lightspeed uwsgi grace period seconds", "2"),
    *section("Lightspeed chatbot"),
    ("lightspeed_chatbot_model_url", "Chatbot LLM server URL (enables chatbot when set)", "https://llm.example.org"),
    ("lightspeed_chatbot_model_verify_ssl", "Verify TLS when connecting to chatbot model server", "true"),
    ("lightspeed_chatbot_default_provider", "Chatbot provider: rhoai, openai, or azure", "rhoai"),
    ("lightspeed_chatbot_http_port", "Chatbot nginx HTTP port", "8085"),
    ("lightspeed_chatbot_https_port", "Chatbot nginx HTTPS port", "8449"),
    ("lightspeed_chatbot_disable_https", "Serve chatbot over HTTP only", "false"),
    ("lightspeed_chatbot_tls_cert", "Chatbot TLS certificate path", "/path/to/chatbot.crt"),
    ("lightspeed_chatbot_tls_key", "Chatbot TLS private key path", "/path/to/chatbot.key"),
    ("lightspeed_chatbot_model_id", "Chatbot model identifier", "my-model"),
    ("lightspeed_chatbot_model_api_key", "Chatbot model API key or access token", "<set your own>"),
    ("lightspeed_chatbot_model_extra_settings", "Extra chatbot model settings dictionary; use vars.yml", None),
    ("lightspeed_chatbot_agent_extra_settings", "Extra chatbot agent settings dictionary; use vars.yml", None),
    *section("Lightspeed MCP tools"),
    ("lightspeed_mcp_controller_enabled", "Expose MCP tools endpoint integrated with Automation Controller", "false"),
    ("lightspeed_mcp_controller_port", "Lightspeed MCP Controller sidecar port", "8004"),
    ("lightspeed_mcp_lightspeed_enabled", "Expose MCP tools endpoint integrated with Lightspeed chatbot", "false"),
    ("lightspeed_mcp_lightspeed_port", "Lightspeed MCP Lightspeed sidecar port", "8005"),
    *section("Lightspeed Watson Code Assistant (WCA)"),
    ("lightspeed_wca_model_type", "WCA deployment mode: wca (cloud) or wca-onprem", "wca"),
    ("lightspeed_wca_model_url", "IBM watsonx Code Assistant API URL", "https://api.dataplatform.cloud.ibm.com"),
    ("lightspeed_wca_model_api_key", "IBM watsonx Code Assistant API key", "<set your own>"),
    ("lightspeed_wca_model_id", "IBM watsonx Code Assistant model ID", "my-wca-model"),
    ("lightspeed_wca_model_verify_ssl", "Verify TLS for WCA model API", "true"),
    ("lightspeed_wca_model_enable_anonymization", "Anonymize PII sent to WCA model", "true"),
    ("lightspeed_wca_model_username", "IBM Cloud Pak username for WCA on-prem deployments", "cpadmin"),
    ("lightspeed_wca_health_check", "Enable WCA model health check", "true"),
    ("lightspeed_wca_idp_url", "WCA identity provider URL (WCA cloud with IDP auth)", "https://idp.example.org"),
    ("lightspeed_wca_idp_login", "WCA IDP login username", "wca-user"),
    ("lightspeed_wca_idp_password", "WCA IDP login password", "<set your own>"),
]

MCP_VARS = [
    *section("Ansible MCP Server"),
    ("mcp_nginx_disable_hsts", "Disable HSTS on MCP Server nginx", "false"),
    ("mcp_nginx_disable_https", "Serve MCP Server over HTTP only", "false"),
    ("mcp_nginx_hsts_max_age", "MCP Server HSTS max-age in seconds", "63072000"),
    ("mcp_nginx_http_port", "MCP Server nginx HTTP port", "8086"),
    ("mcp_nginx_https_port", "MCP Server nginx HTTPS port", "8448"),
    ("mcp_nginx_https_protocols", "MCP Server nginx SSL protocols; list — use vars.yml", None),
    ("mcp_nginx_user_headers", "Custom MCP Server nginx headers; list — use vars.yml", None),
    ("mcp_ignore_certificate_errors", "Ignore SSL certificate errors for upstream AAP connections", "false"),
    ("mcp_public_base_url", "Public base URL of the AAP deployment for MCP Server", "https://aap.example.org"),
    ("mcp_allow_write_operations", "Allow MCP Server write operations against AAP", "false"),
    ("mcp_extra_settings", "Extra MCP Server settings; list — use vars.yml", None),
]

METRICS_VARS = [
    *section("Automation Metrics Service (AAP 2.6+)"),
    ("automationmetrics_api_port", "Internal Metrics Service application port (localhost only)", "8006"),
    ("automationmetrics_controller_db", "Automation Controller database name for read-only metrics access", "awx"),
    ("automationmetrics_controller_pg_username", "Read-only PostgreSQL user for Controller database access", "ms_awx_readonly"),
    ("automationmetrics_controller_read_pg_password", "Password for read-only Controller database user", "<set your own>"),
    ("automationmetrics_dispatcherd_max_tasks", "Dispatcherd max tasks before worker recycle", "100"),
    ("automationmetrics_dispatcherd_timeout", "Dispatcherd worker timeout in seconds", "1200"),
    ("automationmetrics_dispatcherd_workers", "Dispatcherd worker count", "4"),
    ("automationmetrics_extra_settings", "Extra Metrics Service settings; list — use vars.yml", None),
    ("automationmetrics_firewall_zone", "firewalld zone for Metrics Service", "public"),
    ("automationmetrics_gunicorn_timeout", "Metrics Service gunicorn timeout seconds", "10"),
    ("automationmetrics_gunicorn_workers", "Metrics Service gunicorn workers (default: 2 * CPU + 1)", "5"),
    ("automationmetrics_jwt_key", "JWT validation key for Gateway SSO (defaults to Gateway proxy URL)", "https://aap.example.org"),
    ("automationmetrics_nginx_client_max_body_size", "Metrics Service nginx client_max_body_size", "5m"),
    ("automationmetrics_nginx_disable_hsts", "Disable HSTS on Metrics Service nginx", "false"),
    ("automationmetrics_nginx_disable_https", "Serve Metrics Service over HTTP only", "false"),
    ("automationmetrics_nginx_hsts_max_age", "Metrics Service HSTS max-age in seconds", "63072000"),
    ("automationmetrics_nginx_http_port", "Metrics Service nginx HTTP port", "8087"),
    ("automationmetrics_nginx_https_port", "Metrics Service nginx HTTPS port", "8450"),
    ("automationmetrics_nginx_https_protocols", "Metrics Service nginx SSL protocols; list — use vars.yml", None),
    ("automationmetrics_nginx_read_timeout", "Metrics Service nginx read timeout seconds", "15"),
    ("automationmetrics_nginx_user_headers", "Custom Metrics Service nginx headers; list — use vars.yml", None),
    ("automationmetrics_pg_cert_auth", "Use certificate authentication for Metrics Service PostgreSQL", "false"),
    ("automationmetrics_pg_port", "Metrics Service PostgreSQL port", "5432"),
    ("automationmetrics_pg_sslmode", "Metrics Service PostgreSQL sslmode", "prefer"),
    ("automationmetrics_pg_tls_cert", "Client TLS certificate for Metrics Service PostgreSQL", "/path/to/metrics-db.crt"),
    ("automationmetrics_pg_tls_key", "Client TLS key for Metrics Service PostgreSQL", "/path/to/metrics-db.key"),
    ("automationmetrics_pg_username", "Metrics Service PostgreSQL username", "metrics_service"),
    ("automationmetrics_scheduler_check_interval", "Metrics scheduler polling interval in seconds", "30"),
    ("automationmetrics_secret_key", "Metrics Service secret key (auto-generated if unset)", "<set your own>"),
    ("automationmetrics_tls_cert", "Metrics Service TLS certificate path", "/path/to/metrics.crt"),
    ("automationmetrics_tls_key", "Metrics Service TLS private key path", "/path/to/metrics.key"),
    ("automationmetrics_tls_remote", "Metrics Service TLS files are on the Metrics host", "false"),
    ("automationmetrics_use_archive_compression", "Compress Metrics Service backup archives", "true"),
    ("automationmetrics_use_db_compression", "Compress Metrics Service database dumps", "false"),
]


def render_optional_vars(entries: list[tuple[str, str, str | None]], skip: set[str]) -> list[str]:
    lines: list[str] = []
    for name, comment, example in entries:
        if name == "__SECTION__":
            lines.append("")
            lines.append(f"# {comment}")
            if example:
                lines.append(f"# {example}")
            lines.append("# -----------------------------------------------------")
            continue
        if name in skip:
            continue
        if example is None:
            hint = comment.replace("; use vars.yml", "").replace(" — use vars.yml", "")
            lines.append(f"# {name}=  # {hint}; see vars-example.yml")
        else:
            lines.append(f"# {name}={example}  # {comment}")
    return lines


# Variables whose values are lists of {setting, value} dicts (Django/settings.py style)
_SETTING_VALUE_LIST_VARS = {
    "postgresql_extra_settings",
    "gateway_extra_settings",
    "controller_extra_settings",
    "metrics_utility_extra_settings",
    "hub_extra_settings",
    "eda_extra_settings",
    "automationmetrics_extra_settings",
    "mcp_extra_settings",
}

# Variables whose values are free-form dictionaries
_DICT_VARS = {
    "feature_flags",
    "hub_galaxy_importer",
    "hub_azure_extra_settings",
    "hub_s3_extra_settings",
    "lightspeed_chatbot_model_extra_settings",
    "lightspeed_chatbot_agent_extra_settings",
}

# Variables whose values are lists of plain strings
_STRING_LIST_VARS = {
    "hub_data_path_exclude",
    "controller_postinstall_ignore_files",
    "hub_postinstall_ignore_files",
    "eda_safe_plugins",
    "receptor_peers",
}

_IMAGE_LIST_VARS = {"ee_extra_images", "de_extra_images"}


def _yaml_example_body(name: str) -> list[str]:
    """Return commented YAML example lines for a complex inventory variable."""
    if name in _SETTING_VALUE_LIST_VARS:
        example_key = "OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS']"
        if name == "postgresql_extra_settings":
            example_key = "ssl_ciphers"
        elif name == "controller_extra_settings":
            example_key = "USE_X_FORWARDED_HOST"
        elif name == "eda_extra_settings":
            example_key = "RULEBOOK_READINESS_TIMEOUT_SECONDS"
        elif name == "hub_extra_settings":
            example_key = "REDIRECT_IS_HTTPS"
        elif name == "metrics_utility_extra_settings":
            example_key = "SOME_METRICS_SETTING"
        elif name == "automationmetrics_extra_settings":
            example_key = "SOME_SETTING"
        example_value = "'HIGH:!aNULL:!MD5'" if name == "postgresql_extra_settings" else "true"
        if name == "eda_extra_settings":
            example_value = "120"
        return [
            f"# {name}:",
            "#   - setting: " + example_key,
            f"#     value: {example_value}",
        ]

    if name == "feature_flags":
        return [
            "# feature_flags:",
            "#   feature_example_flag: true",
        ]

    if name == "hub_galaxy_importer":
        return [
            "# hub_galaxy_importer:",
            "#   ansible_test_local_image: false",
        ]

    if name == "hub_azure_extra_settings":
        return [
            "# hub_azure_extra_settings:",
            "#   AZURE_LOCATION: foo",
            "#   AZURE_SSL: true",
            "#   AZURE_URL_EXPIRATION_SECS: 60",
        ]

    if name == "hub_s3_extra_settings":
        return [
            "# hub_s3_extra_settings:",
            "#   AWS_S3_MAX_MEMORY_SIZE: 4096",
            "#   AWS_S3_REGION_NAME: eu-central-1",
            "#   AWS_S3_USE_SSL: true",
        ]

    if name == "lightspeed_chatbot_model_extra_settings":
        return [
            "# lightspeed_chatbot_model_extra_settings:",
            "#   api_version: '1.0.1'",
            "#   api_type: ''",
        ]

    if name == "lightspeed_chatbot_agent_extra_settings":
        return [
            "# lightspeed_chatbot_agent_extra_settings:",
            "#   chatbot_temperature_override: 1.0",
        ]

    if name.endswith("_nginx_https_protocols"):
        return [
            f"# {name}:",
            "#   - TLSv1.2",
            "#   - TLSv1.3",
        ]

    if name.endswith("_nginx_user_headers"):
        return [
            f"# {name}:",
            '#   - \'X-Custom-Header "value"\'',
        ]

    if name in _IMAGE_LIST_VARS:
        item_name = "my-custom-ee" if name == "ee_extra_images" else "my-custom-de"
        return [
            f"# {name}:",
            f"#   - name: {item_name}",
            "#     image: registry.example.org/my-ee:latest",
        ]

    if name == "receptor_peers":
        return [
            "# receptor_peers:",
            "#   - exec1.example.org",
            "#   - exec2.example.org",
        ]

    if name in _STRING_LIST_VARS:
        return [
            f"# {name}:",
            "#   - example-entry",
        ]

    return [f"# {name}: []"]


def build_vars_example(entries: list[tuple[str, str, str | None]]) -> str:
    """Build vars-example.yml with every YAML-only variable commented out."""
    lines = [
        "---",
        "# AAP 2.6 optional variables — YAML-only (lists and dictionaries)",
        "#",
        "# Scalar options belong in the inventory file (see inventory-example or",
        "# inventory-growth-example). This file covers complex types that do not",
        "# work well in INI inventory syntax.",
        "#",
        "# Usage:",
        "#   1. Copy this file to vars.yml (or merge into group_vars/all.yml)",
        "#   2. Uncomment and edit the variables you need",
        "#   3. Run: ansible-playbook -i inventory ansible.containerized_installer.install -e @vars.yml",
        "#",
        "# Regenerate from catalog: python3 scripts/build-inventory-2.6.py",
        "",
    ]

    current_section = None
    for name, comment, example in entries:
        if name == "__SECTION__":
            lines.extend(["", f"# {comment}", "# -----------------------------------------------------"])
            current_section = comment
            continue
        if example is not None:
            continue
        hint = comment.replace("; use vars.yml", "").replace(" — use vars.yml", "")
        lines.append("")
        lines.append(f"# {hint}")
        lines.extend(_yaml_example_body(name))

    lines.append("")
    return "\n".join(lines)


ENTERPRISE_ENABLED = {
    "postgresql_admin_username",
    "postgresql_admin_password",
    "registry_username",
    "registry_password",
    "gateway_admin_password",
    "gateway_pg_host",
    "gateway_pg_database",
    "gateway_pg_username",
    "gateway_pg_password",
    "controller_admin_password",
    "controller_pg_host",
    "controller_pg_database",
    "controller_pg_username",
    "controller_pg_password",
    "hub_admin_password",
    "hub_pg_host",
    "hub_pg_database",
    "hub_pg_username",
    "hub_pg_password",
    "eda_admin_password",
    "eda_pg_host",
    "eda_pg_database",
    "eda_pg_username",
    "eda_pg_password",
}

GROWTH_ENABLED = {
    "ansible_connection",
    "postgresql_admin_username",
    "postgresql_admin_password",
    "registry_username",
    "registry_password",
    "redis_mode",
    "gateway_admin_password",
    "gateway_pg_host",
    "gateway_pg_password",
    "controller_admin_password",
    "controller_pg_host",
    "controller_pg_password",
    "controller_percent_memory_capacity",
    "hub_admin_password",
    "hub_pg_host",
    "hub_pg_password",
    "hub_seed_collections",
    "eda_admin_password",
    "eda_pg_host",
    "eda_pg_password",
}

ENTERPRISE_ENABLED_VALUES = {
    "postgresql_admin_username": "<set your own>",
    "postgresql_admin_password": "<set your own>",
    "registry_username": "<your RHN username>",
    "registry_password": "<your RHN password>",
    "gateway_admin_password": "<set your own>",
    "gateway_pg_host": "externaldb.example.org",
    "gateway_pg_database": "<set your own>",
    "gateway_pg_username": "<set your own>",
    "gateway_pg_password": "<set your own>",
    "controller_admin_password": "<set your own>",
    "controller_pg_host": "externaldb.example.org",
    "controller_pg_database": "<set your own>",
    "controller_pg_username": "<set your own>",
    "controller_pg_password": "<set your own>",
    "hub_admin_password": "<set your own>",
    "hub_pg_host": "externaldb.example.org",
    "hub_pg_database": "<set your own>",
    "hub_pg_username": "<set your own>",
    "hub_pg_password": "<set your own>",
    "eda_admin_password": "<set your own>",
    "eda_pg_host": "externaldb.example.org",
    "eda_pg_database": "<set your own>",
    "eda_pg_username": "<set your own>",
    "eda_pg_password": "<set your own>",
}

GROWTH_ENABLED_VALUES = {
    "ansible_connection": "local",
    "postgresql_admin_username": "postgres",
    "postgresql_admin_password": "<set your own>",
    "registry_username": "<your RHN username>",
    "registry_password": "<your RHN password>",
    "redis_mode": "standalone",
    "gateway_admin_password": "<set your own>",
    "gateway_pg_host": "aap.example.org",
    "gateway_pg_password": "<set your own>",
    "controller_admin_password": "<set your own>",
    "controller_pg_host": "aap.example.org",
    "controller_pg_password": "<set your own>",
    "controller_percent_memory_capacity": "0.5",
    "hub_admin_password": "<set your own>",
    "hub_pg_host": "aap.example.org",
    "hub_pg_password": "<set your own>",
    "hub_seed_collections": "false",
    "eda_admin_password": "<set your own>",
    "eda_pg_host": "aap.example.org",
    "eda_pg_password": "<set your own>",
}

LIGHTSPEED_COMMENT_BLOCK = """# AAP Lightspeed
# https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#lightspeed-variables
# -----------------------------------------------------
# lightspeed_admin_password=<set your own>
# lightspeed_pg_host=externaldb.example.org
# lightspeed_pg_password=<set your own>

# In case chatbot is enabled, the default provider is "rhoai"
# lightspeed_chatbot_model_url=<set your own>
# lightspeed_chatbot_model_api_key=<set your own>
# lightspeed_chatbot_model_id=<set your own>

# In case "azure" provider
# lightspeed_chatbot_default_provider = "azure"

# In case "openai" provider
# lightspeed_chatbot_default_provider = "openai"

# lightspeed_mcp_controller_enabled=true
# lightspeed_mcp_lightspeed_enabled=true
# lightspeed_wca_model_api_key=<set your own>
# lightspeed_wca_model_id=<set your own>"""

LIGHTSPEED_COMMENT_BLOCK_GROWTH = LIGHTSPEED_COMMENT_BLOCK.replace(
    "externaldb.example.org", "aap.example.org"
)

ALL_OPTIONAL = (
    CATALOG
    + GATEWAY_VARS
    + CONTROLLER_VARS
    + HUB_VARS
    + EDA_VARS
    + LIGHTSPEED_VARS
    + MCP_VARS
    + METRICS_VARS
)

# Variables already covered by the starter Lightspeed comment block or enabled sections
LIGHTSPEED_STARTER = {
    "lightspeed_admin_password",
    "lightspeed_pg_host",
    "lightspeed_pg_password",
    "lightspeed_chatbot_model_url",
    "lightspeed_chatbot_model_api_key",
    "lightspeed_chatbot_model_id",
    "lightspeed_chatbot_default_provider",
    "lightspeed_mcp_controller_enabled",
    "lightspeed_mcp_lightspeed_enabled",
    "lightspeed_wca_model_api_key",
    "lightspeed_wca_model_id",
}


def build_enabled_section(enabled: set[str], values: dict[str, str]) -> list[str]:
    order = [
        ("ansible_connection", "Ansible", None),
        ("Common variables", "Common variables", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#general-variables"),
        ("gateway", "AAP Gateway", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#platform-gateway-variables"),
        ("controller", "AAP Controller", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#controller-variables"),
        ("hub", "AAP Automation Hub", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#hub-variables"),
        ("eda", "AAP EDA Controller", "https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars#event-driven-ansible-variables"),
    ]

    groups = {
        "ansible_connection": {"ansible_connection"},
        "Common variables": {
            "postgresql_admin_username",
            "postgresql_admin_password",
            "registry_username",
            "registry_password",
            "redis_mode",
        },
        "gateway": {
            "gateway_admin_password",
            "gateway_pg_host",
            "gateway_pg_database",
            "gateway_pg_username",
            "gateway_pg_password",
        },
        "controller": {
            "controller_admin_password",
            "controller_pg_host",
            "controller_pg_database",
            "controller_pg_username",
            "controller_pg_password",
            "controller_percent_memory_capacity",
        },
        "hub": {
            "hub_admin_password",
            "hub_pg_host",
            "hub_pg_database",
            "hub_pg_username",
            "hub_pg_password",
            "hub_seed_collections",
        },
        "eda": {
            "eda_admin_password",
            "eda_pg_host",
            "eda_pg_database",
            "eda_pg_username",
            "eda_pg_password",
        },
    }

    lines: list[str] = ["[all:vars]", ""]
    for key, title, url in order:
        vars_in_group = groups[key] & enabled
        if not vars_in_group:
            continue
        if key == "ansible_connection":
            lines.append("# Ansible")
        else:
            lines.append(f"# {title}")
            if url:
                lines.append(f"# {url}")
            lines.append("# -----------------------------------------------------")
        for var in sorted(vars_in_group, key=lambda v: list(values.keys()).index(v) if v in values else 999):
            lines.append(f"{var}={values[var]}")
        lines.append("")

    return lines


def build_file(header: list[str], host_sections: list[str], enabled: set[str], values: dict[str, str], lightspeed_block: str, topology_skip_extra: set[str]) -> str:
    skip = enabled | LIGHTSPEED_STARTER | topology_skip_extra
    optional = render_optional_vars(ALL_OPTIONAL, skip)

    parts = header + host_sections + build_enabled_section(enabled, values)
    parts.append("# Optional variables — uncomment and customize as needed")
    parts.append("# Complex list/dictionary variables are documented here; see vars-example.yml")
    parts.append("# and pass with: ansible-playbook ... -e @vars.yml")
    parts.append("# -----------------------------------------------------")
    parts.extend(optional)
    parts.append("")
    parts.append(lightspeed_block)
    parts.append("")
    return "\n".join(parts)


ENTERPRISE_HEADER = [
    "# This is the AAP enterprise installer inventory file",
    "# Please consult the docs if you're unsure what to add",
    "# For all optional variables please consult the included README.md",
    "# or the Red Hat documentation:",
    "# https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation",
    "",
    "# ENABLED lines below match the upstream AAP 2.6 starter inventory.",
    "# All other supported variables are listed commented out for reference.",
    "",
]

ENTERPRISE_HOSTS = [
    "# This section is for your AAP Gateway host(s)",
    "# -----------------------------------------------------",
    "[automationgateway]",
    "gateway1.example.org",
    "gateway2.example.org",
    "",
    "# This section is for your AAP Controller host(s)",
    "# Optional host var: receptor_type=control or hybrid (default receptor role on controller)",
    "# -----------------------------------------------------",
    "[automationcontroller]",
    "controller1.example.org",
    "controller2.example.org",
    "",
    "# This section is for your AAP Execution host(s)",
    "# Host var receptor_type=hop marks a hop node; omit for execution nodes",
    "# Optional host vars: receptor_protocol=tcp|udp",
    "# -----------------------------------------------------",
    "[execution_nodes]",
    "hop1.example.org receptor_type='hop'",
    "exec1.example.org",
    "exec2.example.org",
    "",
    "# This section is for your AAP Automation Hub host(s)",
    "# -----------------------------------------------------",
    "[automationhub]",
    "hub1.example.org",
    "hub2.example.org",
    "",
    "# This section is for your AAP EDA Controller host(s)",
    "# Optional host var per host: eda_type=hybrid|api|worker|event-stream",
    "# -----------------------------------------------------",
    "[automationeda]",
    "eda1.example.org",
    "eda2.example.org",
    "",
    "# This section is for your AAP Lightspeed host(s)",
    "# -----------------------------------------------------",
    "# [ansiblelightspeed]",
    "# lightspeed1.example.org",
    "# lightspeed2.example.org",
    "",
    "# This section is for your Ansible MCP Server host(s)",
    "# -----------------------------------------------------",
    "# [ansiblemcp]",
    "# mcpserver1.example.org",
    "",
    "# Automation Metrics Service (AAP 2.6+); requires [automationgateway]",
    "# -----------------------------------------------------",
    "# [automationmetrics]",
    "# metrics1.example.org",
    "",
    "# Managed PostgreSQL — not used in enterprise/external-DB topology",
    "# -----------------------------------------------------",
    "# [database]",
    "# db1.example.org",
    "",
    "[redis]",
    "gateway1.example.org",
    "gateway2.example.org",
    "hub1.example.org",
    "hub2.example.org",
    "eda1.example.org",
    "eda2.example.org",
    "",
]

GROWTH_HEADER = [
    "# This is the AAP installer inventory file intended for the Container growth deployment topology.",
    "# This inventory file expects to be run from the host where AAP will be installed.",
    "# Please consult the Ansible Automation Platform product documentation about this topology's tested hardware configuration.",
    "# https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/tested_deployment_models/container-topologies",
    "#",
    "# Please consult the docs if you're unsure what to add",
    "# For all optional variables please consult the included README.md",
    "# or the Ansible Automation Platform documentation:",
    "# https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation",
    "",
    "# ENABLED lines below match the upstream AAP 2.6 inventory-growth starter.",
    "# All other supported variables are listed commented out for reference.",
    "",
]

GROWTH_HOSTS = [
    "# This section is for your AAP Gateway host(s)",
    "# -----------------------------------------------------",
    "[automationgateway]",
    "aap.example.org",
    "",
    "# This section is for your AAP Controller host(s)",
    "# -----------------------------------------------------",
    "[automationcontroller]",
    "aap.example.org",
    "",
    "# This section is for your AAP Automation Hub host(s)",
    "# -----------------------------------------------------",
    "[automationhub]",
    "aap.example.org",
    "",
    "# This section is for your AAP EDA Controller host(s)",
    "# Optional host var: eda_type=hybrid|api|worker|event-stream",
    "# -----------------------------------------------------",
    "[automationeda]",
    "aap.example.org",
    "",
    "# This section is for your AAP Lightspeed host(s)",
    "# -----------------------------------------------------",
    "# [ansiblelightspeed]",
    "# aap.example.org",
    "",
    "# This section is for your Ansible MCP Server host(s)",
    "# -----------------------------------------------------",
    "# [ansiblemcp]",
    "# aap.example.org",
    "",
    "# Automation Metrics Service (AAP 2.6+); requires [automationgateway]",
    "# -----------------------------------------------------",
    "# [automationmetrics]",
    "# aap.example.org",
    "",
    "# Execution nodes — not used in growth/all-in-one topology",
    "# -----------------------------------------------------",
    "# [execution_nodes]",
    "# aap.example.org",
    "",
    "# This section is for the AAP database",
    "# -----------------------------------------------------",
    "[database]",
    "aap.example.org",
    "",
    "# Redis cluster group — not used when redis_mode=standalone (growth default)",
    "# -----------------------------------------------------",
    "# [redis]",
    "# aap.example.org",
    "",
]

# Skip redis_mode in enterprise optional (uses default cluster) and postgresql_admin in optional when enabled
ENTERPRISE_SKIP = set()
GROWTH_SKIP = set()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    enterprise = build_file(
        ENTERPRISE_HEADER,
        ENTERPRISE_HOSTS,
        ENTERPRISE_ENABLED,
        ENTERPRISE_ENABLED_VALUES,
        LIGHTSPEED_COMMENT_BLOCK,
        ENTERPRISE_SKIP,
    )
    growth = build_file(
        GROWTH_HEADER,
        GROWTH_HOSTS,
        GROWTH_ENABLED,
        GROWTH_ENABLED_VALUES,
        LIGHTSPEED_COMMENT_BLOCK_GROWTH,
        GROWTH_SKIP,
    )

    (OUT_DIR / "inventory-example").write_text(enterprise, encoding="utf-8")
    (OUT_DIR / "inventory-growth-example").write_text(growth, encoding="utf-8")

    vars_example = build_vars_example(ALL_OPTIONAL)
    (OUT_DIR / "vars-example.yml").write_text(vars_example, encoding="utf-8")

    print(f"Wrote {OUT_DIR / 'inventory-example'}")
    print(f"Wrote {OUT_DIR / 'inventory-growth-example'}")
    print(f"Wrote {OUT_DIR / 'vars-example.yml'}")


if __name__ == "__main__":
    main()
