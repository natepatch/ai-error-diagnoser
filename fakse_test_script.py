import os
from ai_fixer.rspec_generator import generate_and_write_rspec_test

# Full simulated RSpec output (mocked)
output_lines = [
    "",
    "  82) Types::QueryType#current_account when the account for the current_user does not exist returns nil",
    "      Failure/Error: let(:account) { create(:account, user: user) }",
    "",
    "      NoMethodError:",
    "        undefined method `user=' for #<Account:0x00007ff209641b50>",
    "        Did you mean?  username",
    "      # ./spec/graphql/types/query_type_spec.rb:99:in `block (2 levels) in <main>'",
    "      # ./spec/graphql/types/query_type_spec.rb:103:in `block (2 levels) in <main>'",
    "",
    "  83) Mutations::UserSignIn when email is invalid returns an authentication error",
    "      Failure/Error: post '/graphql', params: { query: mutation }",
    "",
    "      GraphQL::ExecutionError:",
    "        Invalid credentials provided",
    "      # ./spec/graphql/mutations/user_sign_in_spec.rb:45:in `block (2 levels) in <main>'",
    "",
    "  84) Resolvers::OrganisationResolver when organisation does not exist returns nil",
    "      Failure/Error: resolve_organisation(args)",
    "",
    "      ActiveRecord::RecordNotFound:",
    "        Couldn't find Organisation with 'id'=999",
    "      # ./app/graphql/resolvers/organisation_resolver.rb:17:in `resolve'",
    "      # ./spec/graphql/resolvers/organisation_resolver_spec.rb:58:in `block (3 levels) in <main>'",
    "",
    "  85) Types::UserType#full_name returns the concatenated first and last name",
    "      Failure/Error: expect(user.full_name).to eq('John Doe')",
    "",
    "      NameError:",
    "        undefined local variable or method `user' for #<RSpec::ExampleGroups::TypesUserType:0x00007fc2d25e2f18>",
    "      # ./spec/graphql/types/user_type_spec.rb:22:in `block (2 levels) in <main>'",
    "",
    "rspec ./spec/graphql/types/query_type_spec.rb:456 # Types::QueryType#current_account when the current user is logged in returns the account associated with the current user",
    "rspec ./spec/graphql/mutations/user_sign_in_spec.rb:45 # Mutations::UserSignIn when email is invalid returns an authentication error",
    "rspec ./spec/graphql/resolvers/organisation_resolver_spec.rb:58 # Resolvers::OrganisationResolver when organisation does not exist returns nil",
    "rspec ./spec/graphql/types/user_type_spec.rb:22 # Types::UserType#full_name returns the concatenated first and last name",
]

mock_output = "\n".join([line.lstrip() for line in output_lines])

# Set up a dummy spec file
rails_root = "/tmp/fake_patchwork"
os.environ["RAILS_REPO_PATH"] = rails_root
fake_spec_file = os.path.join(rails_root, "spec/models/my_class_spec.rb")
os.makedirs(os.path.dirname(fake_spec_file), exist_ok=True)

with open(fake_spec_file, "w") as f:
    f.write("RSpec.describe MyClass do\nend\n")

# Mocks for all dependencies
def fake_run_spec(spec_path, capture_output=True):
    print("📢 Returning mock RSpec output")
    return False, mock_output

def fake_generate(prompt):
    print("📢 Prompt received by LLM:\n", prompt)
    return "```ruby\nRSpec.describe MyClass do\nend\n```"

def fake_prompt(*args): return "Prompt here"
def fake_infer(_): return "MyClass"
def fake_get_spec_path(_): return "spec/models/my_class_spec.rb"
def fake_ensure(*_): pass
def fake_append(*_): pass
def fake_strip(md): return md.strip("```ruby").strip("```")

# Execute the function under test
spec_path, error_json = generate_and_write_rspec_test(
    class_name="MyClass",
    method_name="bad_method",
    method_code="def bad_method; end",
    app_path="app/models/my_class.rb",
    generate_rspec_block=fake_generate,
    run_spec=fake_run_spec,
    build_rspec_prompt=fake_prompt,
    infer_ruby_constant_from_path=fake_infer,
    get_spec_path=fake_get_spec_path,
    ensure_spec_file_exists=fake_ensure,
    append_test_to_spec=fake_append,
    strip_markdown_fences=fake_strip
)

# Final output
print("\n✅ Parsed JSON output:\n", error_json)
