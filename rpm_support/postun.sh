if [ "$1" = "0" ]; then
    if [ ! "$(ls -A %{aws_bin_path})" ]; then
        rmdir %{aws_bin_path}
    fi

    %__rm -f %{aws_product_path_link}

    if [ ! "$(ls -A %{aws_path}/apitools)" ]; then
        rmdir %{aws_path}/apitools
    fi

    if [ ! "$(ls -A %{aws_path})" ]; then
        rmdir %{aws_path}
    fi
fi