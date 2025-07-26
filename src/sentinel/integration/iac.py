"""Infrastructure as Code export functionality."""

from enum import Enum
from typing import Dict, Any

from sentinel.models.core import Plan, Resource


class IaCFormat(Enum):
    """Supported Infrastructure as Code formats."""
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    PULUMI = "pulumi"
    ANSIBLE = "ansible"


class IaCExporter:
    """Export deployment plans as Infrastructure as Code."""
    
    def export(self, plan: Plan, format: IaCFormat) -> str:
        """Export plan in the specified IaC format."""
        if format == IaCFormat.TERRAFORM:
            return self._export_terraform(plan)
        elif format == IaCFormat.CLOUDFORMATION:
            return self._export_cloudformation(plan)
        elif format == IaCFormat.PULUMI:
            return self._export_pulumi(plan)
        elif format == IaCFormat.ANSIBLE:
            return self._export_ansible(plan)
        else:
            raise ValueError(f"Unsupported IaC format: {format}")
    
    def _export_terraform(self, plan: Plan) -> str:
        """Export plan as Terraform HCL."""
        terraform_code = f"""# {plan.name}
# {plan.description}

terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
    google = {{
      source  = "hashicorp/google"
      version = "~> 4.0"
    }}
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}

"""
        
        # Add provider configurations
        providers = set(resource.provider for resource in plan.resources)
        
        for provider in providers:
            if provider == "aws":
                terraform_code += """provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

"""
            elif provider == "gcp":
                terraform_code += """provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

variable "gcp_project" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

"""
            elif provider == "azure":
                terraform_code += """provider "azurerm" {
  features {}
}

"""
        
        # Add resources
        for i, resource in enumerate(plan.resources):
            terraform_code += self._resource_to_terraform(resource, i)
        
        return terraform_code
    
    def _resource_to_terraform(self, resource: Resource, index: int) -> str:
        """Convert a resource to Terraform HCL."""
        if resource.provider == "aws":
            if resource.service == "ec2":
                return f"""resource "aws_instance" "instance_{index}" {{
  ami           = data.aws_ami.ubuntu.id
  instance_type = "{resource.resource_type}"
  
  tags = {{
    Name = "{resource.resource_type}-{index}"
    Environment = "free-tier"
  }}
}}

data "aws_ami" "ubuntu" {{
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {{
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }}
}}

"""
            elif resource.service == "s3":
                return f"""resource "aws_s3_bucket" "bucket_{index}" {{
  bucket = "free-tier-bucket-{index}-${{random_id.bucket_suffix.hex}}"
  
  tags = {{
    Environment = "free-tier"
  }}
}}

resource "random_id" "bucket_suffix" {{
  byte_length = 8
}}

"""
        
        elif resource.provider == "gcp":
            if resource.service == "compute":
                return f"""resource "google_compute_instance" "instance_{index}" {{
  name         = "free-tier-instance-{index}"
  machine_type = "{resource.resource_type}"
  zone         = "${{var.gcp_region}}-a"
  
  boot_disk {{
    initialize_params {{
      image = "debian-cloud/debian-11"
    }}
  }}
  
  network_interface {{
    network = "default"
    access_config {{
      // Ephemeral public IP
    }}
  }}
  
  tags = ["free-tier"]
}}

"""
        
        return f"# Unsupported resource: {resource.provider}:{resource.service}\n"
    
    def _export_cloudformation(self, plan: Plan) -> str:
        """Export plan as AWS CloudFormation YAML."""
        cf_template = f"""AWSTemplateFormatVersion: '2010-09-09'
Description: '{plan.description}'

Parameters:
  InstanceType:
    Type: String
    Default: t2.micro
    AllowedValues:
      - t2.micro
      - t3.micro
    Description: EC2 instance type for free tier

Resources:
"""
        
        for i, resource in enumerate(plan.resources):
            if resource.provider == "aws" and resource.service == "ec2":
                cf_template += f"""  Instance{i}:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !Ref LatestAmiId
      InstanceType: {resource.resource_type}
      Tags:
        - Key: Name  
          Value: free-tier-instance-{i}
        - Key: Environment
          Value: free-tier

"""
        
        cf_template += """  LatestAmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2

Outputs:
  InstanceIds:
    Description: Instance IDs
    Value: !Join
      - ','
      - !Ref Instance0
"""
        
        return cf_template
    
    def _export_pulumi(self, plan: Plan) -> str:
        """Export plan as Pulumi Python code."""
        pulumi_code = f'''"""
{plan.name}
{plan.description}
"""

import pulumi
import pulumi_aws as aws
import pulumi_gcp as gcp
import pulumi_azure as azure

# Configuration
config = pulumi.Config()

'''
        
        for i, resource in enumerate(plan.resources):
            if resource.provider == "aws" and resource.service == "ec2":
                pulumi_code += f'''
# AWS EC2 Instance {i}
instance_{i} = aws.ec2.Instance("instance-{i}",
    instance_type="{resource.resource_type}",
    ami="ami-0c55b159cbfafe1d0",  # Amazon Linux 2
    tags={{
        "Name": "free-tier-instance-{i}",
        "Environment": "free-tier"
    }}
)

pulumi.export(f"instance_{i}_public_ip", instance_{i}.public_ip)
'''
        
        return pulumi_code
    
    def _export_ansible(self, plan: Plan) -> str:
        """Export plan as Ansible playbook."""
        ansible_yaml = f"""---
# {plan.name}
# {plan.description}

- name: Deploy Free-Tier Resources
  hosts: localhost
  connection: local
  gather_facts: false
  
  vars:
    aws_region: us-east-1
    gcp_project: your-gcp-project
    
  tasks:
"""
        
        for i, resource in enumerate(plan.resources):
            if resource.provider == "aws" and resource.service == "ec2":
                ansible_yaml += f"""
    - name: Launch AWS EC2 instance {i}
      amazon.aws.ec2_instance:
        name: "free-tier-instance-{i}"
        instance_type: "{resource.resource_type}"
        image_id: "ami-0c55b159cbfafe1d0"
        region: "{{{{ aws_region }}}}"
        tags:
          Environment: free-tier
        state: present
      register: ec2_instance_{i}
"""
        
        return ansible_yaml