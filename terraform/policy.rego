package terraform.validation
import rego.v1

# Default allow is false
default allow := false

# List of allowed, cost-effective instance types
allowed_instance_types := {"t3.micro", "t2.micro"}

# Deny deployment if the instance type is NOT in the allowed list
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_instance"
    instance_type := resource.change.after.instance_type
    not allowed_instance_types[instance_type]
    msg := sprintf("OPA POLICY VIOLATION: Instance type '%v' is not allowed. Please use t3.micro.", [instance_type])
}
