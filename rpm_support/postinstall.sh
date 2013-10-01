# Upgrade- remove old symlink
if [ "$1" = "2" ]; then
    %__rm -f %{aws_product_path_link}
    # also remove old init script if it exists
    if [ -e  %{_initrddir}/cfn-resource-bridge ]; then
        %__rm -f  %{_initrddir}/cfn-resource-bridge
    fi
fi

# Install/Upgrade - Create symlink from versioned
# directory to product name directory if it doesn't exist
if [ ! -e  %{aws_product_path_link} ]; then
    %__ln_s  ./%{aws_product_name_v}  %{aws_product_path_link}
fi

# Create aws bin directory if it doesn't exist:
if [ ! -d %{aws_bin_path} ]; then
    %__mkdir %{aws_bin_path}
fi

for command in %{aws_product_path_link}/bin/*; do
    %define command_name $(basename $command)
    if [ -e %{aws_bin_path}/%{command_name} ]; then
        if [ "$1" = "2" ]; then
            # Upgrade- remove old symlinks
            %__rm -f %{aws_bin_path}/%{command_name}
        fi
    fi
    if [ ! -h %{aws_bin_path}/%{command_name} ]; then
    # Install relative symlink from generic directory to aws shared directory
        %__ln_s ../apitools/%{aws_product_name}/bin/%{command_name}  %{aws_bin_path}/%{command_name}
    fi
done

# Create link to init script
if [ ! -e %{_initrddir}/cfn-resource-bridge ]; then
    %__ln_s %{aws_product_path_link}/init/redhat/cfn-resource-bridge  %{_initrddir}/cfn-resource-bridge
fi

%__chmod 755 %{_initrddir}/cfn-resource-bridge
%__chmod 755 %{aws_product_path_link}/init/redhat/cfn-resource-bridge
