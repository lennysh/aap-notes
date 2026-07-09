#!/usr/bin/env python3
"""Generate AAP 2.5 RPM installer inventory examples."""

from build_rpm_inventory import VERSIONS, generate_version

if __name__ == "__main__":
    generate_version(VERSIONS["2.5"])
