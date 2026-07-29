.PHONY: deploy destroy plan

deploy:
	@bash infra/scripts/deploy_stack.sh

destroy:
	@bash infra/scripts/destroy_stack.sh

plan:
	@cd infra/terraform && terraform plan -var-file="terraform.tfvars"