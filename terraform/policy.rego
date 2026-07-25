package terraform.validation

# Default allow is false
default allow = false

# List of allowed, cost-effective instance types
allowed_instance_types = {"t3.micro", "t2.micro"}

# Deny deployment if the instance type is NOT in the allowed list
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_instance"
    instance_type := resource.change.after.instance_type
    not allowed_instance_types[instance_type]
    msg := sprintf("OPA POLICY VIOLATION: Instance type '%v' is not allowed. Please use t3.micro.", [instance_type])
}
