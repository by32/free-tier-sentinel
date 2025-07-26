"""AWS capacity checking implementation."""

from datetime import UTC, datetime

import boto3
from botocore.exceptions import ClientError

from sentinel.capacity.checker import CapacityChecker, CapacityResult


class AWSCapacityChecker(CapacityChecker):
    """Capacity checker for AWS EC2 instances."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize AWS capacity checker."""
        self.provider = "aws"
        self.region = region
        self.ec2_client = boto3.client("ec2", region_name=region)

    def check_availability(self, region: str, resource_type: str) -> CapacityResult:
        """Check availability of an EC2 instance type in a region."""
        try:
            # Check availability zones
            az_response = self.ec2_client.describe_availability_zones(
                Filters=[{"Name": "state", "Values": ["available"]}]
            )
            available_azs = [az["ZoneName"] for az in az_response["AvailabilityZones"]]

            # Check instance type offerings
            offerings_response = self.ec2_client.describe_instance_type_offerings(
                Filters=[
                    {"Name": "instance-type", "Values": [resource_type]},
                    {"Name": "location-type", "Values": ["availability-zone"]},
                ]
            )

            available_offerings = offerings_response["InstanceTypeOfferings"]
            available_in_azs = [
                offering["Location"]
                for offering in available_offerings
                if offering["Location"] in available_azs
            ]

            # Calculate capacity level
            total_azs = len(available_azs)
            available_azs_count = len(available_in_azs)

            if available_azs_count == 0:
                available = False
                capacity_level = 0.0
            else:
                available = True
                capacity_level = (
                    available_azs_count / total_azs if total_azs > 0 else 0.0
                )

            provider_data = {
                "provider": "aws",
                "available_azs": available_in_azs,
                "total_azs": total_azs,
            }

            if capacity_level < 1.0 and capacity_level > 0.0:
                provider_data["limited_availability"] = True

            return CapacityResult(
                region=region,
                resource_type=resource_type,
                available=available,
                capacity_level=capacity_level,
                last_checked=datetime.now(UTC),
                provider_specific_data=provider_data,
            )

        except ClientError as e:
            # Handle AWS API errors
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code in ["Throttling", "RequestLimitExceeded"]:
                raise Exception(f"AWS API rate limit: {error_message}")
            else:
                raise Exception(f"AWS API error: {error_code} - {error_message}")

    def get_available_regions(self) -> list[str]:
        """Get list of available AWS regions."""
        try:
            response = self.ec2_client.describe_regions()
            return [region["RegionName"] for region in response["Regions"]]
        except ClientError as e:
            raise Exception(f"Failed to get AWS regions: {e}")

    def get_supported_resource_types(self) -> list[str]:
        """Get list of supported EC2 instance types."""
        try:
            response = self.ec2_client.describe_instance_types()
            return [instance["InstanceType"] for instance in response["InstanceTypes"]]
        except ClientError as e:
            raise Exception(f"Failed to get AWS instance types: {e}")
