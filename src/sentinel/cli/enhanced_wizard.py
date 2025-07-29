"""Enhanced interactive wizard with beautiful UI and autocomplete."""

import questionary
from questionary import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from typing import List, Dict, Any
from datetime import datetime, UTC

from sentinel.models.core import Resource, Plan
from .planning import SUPPORTED_PROVIDERS


class EnhancedInteractivePlanner:
    """Interactive planner with enhanced UI using Rich and Questionary."""
    
    def __init__(self):
        self.console = Console()
        self.resources: List[Resource] = []
        
    def create_plan(self) -> Plan:
        """Launch enhanced interactive wizard to create a deployment plan."""
        # Welcome screen
        self._show_welcome()
        
        # Step 1: Provider selection with autocomplete
        provider = self._select_provider_enhanced()
        
        # Step 2: Region selection with descriptions
        region = self._select_region_enhanced(provider)
        
        # Step 3: Resource configuration with guided flow
        self._configure_resources_enhanced(provider, region)
        
        # Step 4: Plan metadata with validation
        plan_name, plan_description = self._get_plan_metadata()
        
        # Step 5: Review and confirm
        plan = Plan(
            name=plan_name,
            description=plan_description,
            resources=self.resources
        )
        
        if self._review_and_confirm_plan(plan):
            return plan
        else:
            self.console.print("❌ Plan creation cancelled.", style="red")
            raise KeyboardInterrupt("Plan creation cancelled by user")
    
    def _show_welcome(self) -> None:
        """Display enhanced welcome screen."""
        welcome_text = Text()
        welcome_text.append("🛡️ ", style="bold blue")
        welcome_text.append("Free-Tier Sentinel", style="bold white")
        welcome_text.append(" - Interactive Planner", style="bold cyan")
        
        welcome_panel = Panel(
            Text.assemble(
                welcome_text, "\n\n",
                "This wizard helps you maximize cloud free-tier benefits by:\n",
                "• 🆓 Focusing on free-tier resources by default\n",
                "• 📊 Showing exact free-tier limits and durations\n",
                "• ⚡ Preventing costly overages with smart planning\n\n",
                "✨ Use arrow keys to navigate, Space to select, Enter to confirm.",
                justify="center"
            ),
            title="Welcome - Stay Within Free Tier!",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(welcome_panel)
        self.console.print()
    
    def _select_provider_enhanced(self) -> str:
        """Enhanced provider selection with descriptions and icons."""
        provider_choices = []
        for key, info in SUPPORTED_PROVIDERS.items():
            icon = {
                'aws': '🟠',
                'gcp': '🟡', 
                'azure': '🔵'
            }.get(key, '☁️')
            
            choice_text = f"{icon} {info['name']} ({key})"
            provider_choices.append(questionary.Choice(choice_text, value=key))
        
        provider_answer = questionary.select(
            "🏗️  Which cloud provider would you like to use?",
            choices=provider_choices,
            style=questionary.Style([
                ('selected', 'bg:#0078D4 bold'),
                ('pointer', 'fg:#0078D4 bold'),
                ('highlighted', 'fg:#0078D4'),
                ('answer', 'fg:#44BC84 bold'),
            ])
        ).ask()
        
        if not provider_answer:
            raise KeyboardInterrupt("Provider selection cancelled")
            
        return provider_answer
    
    def _select_region_enhanced(self, provider: str) -> str:
        """Enhanced region selection with descriptions."""
        regions = SUPPORTED_PROVIDERS[provider]['regions']
        
        # Add descriptions for popular regions
        region_info = {
            'us-east-1': 'US East (N. Virginia) - Most services available',
            'us-west-2': 'US West (Oregon) - Lower latency West Coast',
            'eu-west-1': 'EU (Ireland) - GDPR compliant',
            'us-central1': 'US Central (Iowa) - Google\'s main region',
            'europe-west1': 'EU West (Belgium) - Google Europe',
            'eastus': 'East US (Virginia) - Azure primary region',
            'westeurope': 'West Europe (Netherlands) - Azure Europe'
        }
        
        region_choices = []
        for region in regions:
            description = region_info.get(region, 'Standard region')
            choice_text = f"{region} - {description}"
            region_choices.append(questionary.Choice(choice_text, value=region))
        
        region_answer = questionary.select(
            f"🌍 Which region would you like to deploy in?",
            choices=region_choices,
            style=questionary.Style([
                ('selected', 'bg:#0078D4 bold'),
                ('pointer', 'fg:#0078D4 bold'),
                ('answer', 'fg:#44BC84 bold'),
            ])
        ).ask()
        
        if not region_answer:
            raise KeyboardInterrupt("Region selection cancelled")
            
        return region_answer
    
    def _configure_resources_enhanced(self, provider: str, region: str) -> None:
        """Enhanced resource configuration with guided flow."""
        self.console.print(f"\n🔧 Configuring resources for {provider} in {region}")
        
        # Show free-tier summary for the selected provider
        self._show_free_tier_summary(provider)
        
        # Ask if user wants to see paid resources
        show_paid = questionary.confirm(
            "Would you like to see paid resources in addition to free-tier?",
            default=False
        ).ask()
        
        # Define resource types with descriptions and free-tier info
        resource_types = {
            'aws': {
                'compute': {
                    'ec2': {
                        't2.micro': {'desc': '750 hours/month (12 months), 1 vCPU, 1GB RAM', 'free': True},
                        't2.small': {'desc': '1 vCPU, 2GB RAM', 'free': False},
                        't3.micro': {'desc': '2 vCPU, 1GB RAM', 'free': False}
                    }
                },
                'storage': {
                    's3': {
                        'standard_storage': {'desc': '5GB storage, 20K GET, 2K PUT requests/month', 'free': True},
                        'intelligent_tiering': {'desc': 'Automatic cost optimization', 'free': False}
                    }
                },
                'database': {
                    'rds': {
                        'db.t3.micro': {'desc': '750 hours/month (12 months), 20GB storage', 'free': True},
                        'db.t3.small': {'desc': 'Better performance', 'free': False}
                    }
                }
            },
            'gcp': {
                'compute': {
                    'compute': {
                        'e2-micro': {'desc': '30GB-months HDD, 1GB network egress (always free)', 'free': True},
                        'e2-small': {'desc': '2 vCPU (shared), 2GB RAM', 'free': False}
                    }
                },
                'storage': {
                    'storage': {
                        'standard_storage': {'desc': '5GB-months, 5K operations/month (always free)', 'free': True},
                        'nearline_storage': {'desc': 'Infrequent access storage', 'free': False}
                    }
                },
                'database': {
                    'firestore': {
                        'standard': {'desc': '1GB storage, 50K reads, 20K writes/day (always free)', 'free': True}
                    }
                }
            },
            'azure': {
                'compute': {
                    'vm': {
                        'Standard_B1s': {'desc': '750 hours/month (12 months), 1 vCPU, 1GB RAM', 'free': True},
                        'Standard_B2s': {'desc': '2 vCPU, 4GB RAM', 'free': False}
                    }
                },
                'storage': {
                    'storage': {
                        'standard_storage': {'desc': '5GB LRS blob storage (12 months)', 'free': True},
                        'premium_storage': {'desc': 'High performance SSD storage', 'free': False}
                    }
                },
                'database': {
                    'cosmos': {
                        'serverless': {'desc': '1000 RU/s, 25GB storage/month (always free)', 'free': True}
                    }
                }
            }
        }
        
        # Interactive resource selection
        while True:
            # Ask what type of resource to add
            categories = list(resource_types[provider].keys())
            category_choices = []
            for cat in categories:
                icon = {'compute': '💻', 'storage': '💾', 'database': '🗄️'}.get(cat, '⚙️')
                category_choices.append(questionary.Choice(f"{icon} {cat.title()}", value=cat))
            
            category_choices.append(questionary.Choice("✅ Finish adding resources", value="done"))
            
            category = questionary.select(
                "What type of resource would you like to add?",
                choices=category_choices
            ).ask()
            
            if not category or category == "done":
                break
                
            # Select service within category
            services = list(resource_types[provider][category].keys())
            if len(services) == 1:
                service = services[0]
            else:
                service = questionary.select(
                    f"Which {category} service?",
                    choices=services
                ).ask()
                
            if not service:
                continue
                
            # Select resource type with descriptions
            resource_options = resource_types[provider][category][service]
            resource_choices = []
            for res_type, info in resource_options.items():
                # Skip paid resources if user doesn't want to see them
                if not show_paid and not info['free']:
                    continue
                    
                free_indicator = "🆓" if info['free'] else "💰"
                free_label = "Always Free" if provider == 'gcp' and info['free'] else "Free Tier" if info['free'] else "Paid"
                choice_text = f"{free_indicator} {res_type} - {free_label}: {info['desc']}"
                resource_choices.append(questionary.Choice(choice_text, value=res_type))
            
            if not resource_choices:
                self.console.print(f"No free-tier options available for {service}. Skipping...", style="yellow")
                continue
            
            resource_type = questionary.select(
                f"Which {service} resource type?",
                choices=resource_choices
            ).ask()
            
            if not resource_type:
                continue
            
            # Get quantity and usage
            quantity = questionary.text(
                "How many instances?",
                default="1",
                validate=lambda x: x.isdigit() and int(x) > 0
            ).ask()
            
            if not quantity:
                continue
                
            usage = questionary.text(
                "Estimated monthly usage (hours for compute, GB for storage)?",
                default="100",
                validate=lambda x: x.isdigit() and int(x) > 0
            ).ask()
            
            if not usage:
                continue
            
            # Create resource
            resource = Resource(
                provider=provider,
                service=service,
                resource_type=resource_type,
                region=region,
                quantity=int(quantity),
                estimated_monthly_usage=int(usage)
            )
            
            self.resources.append(resource)
            
            # Show added resource
            self.console.print(f"✅ Added: {resource.service} {resource.resource_type} x{resource.quantity}", style="green")
            
        if not self.resources:
            self.console.print("⚠️  No resources added. Adding a default t2.micro instance.", style="yellow")
            default_resource = Resource(
                provider=provider,
                service="ec2" if provider == "aws" else "compute" if provider == "gcp" else "vm",
                resource_type="t2.micro" if provider == "aws" else "e2-micro" if provider == "gcp" else "Standard_B1s",
                region=region,
                quantity=1,
                estimated_monthly_usage=100
            )
            self.resources.append(default_resource)
    
    def _get_plan_metadata(self) -> tuple[str, str]:
        """Get plan name and description with validation."""
        plan_name = questionary.text(
            "📝 Enter a name for your plan:",
            default=f"free-tier-plan-{datetime.now(UTC).strftime('%Y%m%d')}",
            validate=lambda x: len(x.strip()) >= 3
        ).ask()
        
        if not plan_name:
            raise KeyboardInterrupt("Plan name input cancelled")
        
        plan_description = questionary.text(
            "📄 Enter a description for your plan:",
            default="Free-tier resource deployment created with interactive wizard"
        ).ask()
        
        if not plan_description:
            plan_description = "Free-tier resource deployment"
            
        return plan_name.strip(), plan_description.strip()
    
    def _show_free_tier_summary(self, provider: str) -> None:
        """Show a summary of free-tier offerings for the selected provider."""
        summaries = {
            'aws': {
                'title': '🟠 AWS Free Tier (12 months)',
                'offerings': [
                    '• EC2: 750 hours t2.micro per month',
                    '• S3: 5GB standard storage + 20K GET requests',
                    '• RDS: 750 hours db.t3.micro + 20GB storage',
                    '• Lambda: 1M requests + 400K GB-seconds always free',
                    '• DynamoDB: 25GB storage + 25 units R/W always free'
                ],
                'note': '⚠️  Most expire after 12 months!'
            },
            'gcp': {
                'title': '🟡 GCP Always Free Tier',
                'offerings': [
                    '• Compute: 1 e2-micro instance (30GB HDD)',
                    '• Storage: 5GB Cloud Storage',
                    '• Firestore: 1GB storage + 50K reads/day',
                    '• Cloud Functions: 2M invocations/month',
                    '• BigQuery: 1TB queries/month'
                ],
                'note': '✅ No expiration - always free!'
            },
            'azure': {
                'title': '🔵 Azure Free Tier',
                'offerings': [
                    '• VMs: 750 hours B1s (12 months)',
                    '• Storage: 5GB LRS blob (12 months)',
                    '• Cosmos DB: 1000 RU/s + 25GB always free',
                    '• Functions: 1M requests/month always free',
                    '• SQL Database: 250GB (12 months)'
                ],
                'note': '⚠️  Mix of 12-month and always-free'
            }
        }
        
        summary = summaries[provider]
        panel = Panel(
            Text.assemble(
                Text(summary['title'], style="bold"),
                "\n\n",
                "\n".join(summary['offerings']),
                "\n\n",
                Text(summary['note'], style="italic yellow")
            ),
            title="📋 Free Tier Summary",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def _review_and_confirm_plan(self, plan: Plan) -> bool:
        """Show plan review and get confirmation."""
        self.console.print("\n" + "="*60)
        self.console.print("📋 Plan Review", style="bold blue")
        self.console.print("="*60)
        
        # Plan summary table
        table = Table(title=f"Plan: {plan.name}")
        table.add_column("Service", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Quantity", justify="right", style="green")
        table.add_column("Usage", justify="right", style="yellow")
        table.add_column("Region", style="blue")
        
        for resource in plan.resources:
            table.add_row(
                resource.service,
                resource.resource_type,
                str(resource.quantity),
                f"{resource.estimated_monthly_usage}h",
                resource.region
            )
        
        self.console.print(table)
        self.console.print(f"\n📊 Total estimated cost: ${plan.total_estimated_cost}")
        self.console.print(f"📝 Description: {plan.description}")
        
        # Confirmation
        confirm = questionary.confirm(
            "\n🚀 Create this plan?",
            default=True
        ).ask()
        
        return confirm if confirm is not None else False