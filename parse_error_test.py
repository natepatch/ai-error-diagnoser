import re
import json

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

full_failures = []
collecting = False
current_block = []

for line in output_lines:
    clean_line = line.strip()

    # Start of a new failure block
    if re.match(r"^\d+\)", clean_line):
        if current_block:
            full_failures.append(current_block)
        collecting = True
        current_block = [clean_line]
        continue

    if collecting:
        if clean_line.startswith("rspec "):
            collecting = False
            if current_block:
                full_failures.append(current_block)
                current_block = []
            continue
        current_block.append(line.rstrip())

# Add final block if any
if current_block:
    full_failures.append(current_block)

parsed = []

for block in full_failures:
    if not block:
        continue

    header = block[0]
    index_match = re.match(r"^(\d+)\)\s+(.*)", header)
    if not index_match:
        continue

    index = int(index_match.group(1))
    description = index_match.group(2)

    error_type = ""
    message = ""
    hint = None
    file_paths = []

    for i, line in enumerate(block[1:], start=1):
        if not error_type:
            err_match = re.match(r"\s*(\w+::)?(\w+Error):", line)
            if err_match:
                error_type = f"{err_match.group(1) or ''}{err_match.group(2)}"
                # Get message on next line if exists
                if i + 1 < len(block):
                    msg_line = block[i + 1].strip()
                    if msg_line:
                        message = msg_line
                continue

        hint_match = re.match(r"\s*Did you mean\?\s+(.*)", line)
        if hint_match:
            hint = hint_match.group(1).strip()
            continue

        file_match = re.match(r"\s*#\s+(.+):(\d+)", line)
        if file_match:
            file_paths.append({
                "path": file_match.group(1).strip(),
                "line": int(file_match.group(2))
            })

    parsed.append({
        "index": index,
        "description": description,
        "error_type": error_type,
        "message": message,
        "hint": hint,
        "file_paths": file_paths
    })

# Print JSON
print(json.dumps(parsed, indent=2))
