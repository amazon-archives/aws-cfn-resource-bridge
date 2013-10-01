# Uninstall: 
if [ "$1" = "0" ]; then
    #Clean up the symlinks if it points to this version
    if [ "x$(readlink %{aws_product_path_link})" == "x./%{aws_product_name_v}" ]; then
        for command in %{aws_bin_path}/cfn*; do
            if [ "x$(readlink $command)" == "x../apitools/%{aws_product_name}/bin/$(basename $command)" ]; then
                %__rm -f $command
            fi
        done
    fi
fi