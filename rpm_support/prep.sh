%define          aws_product_name                      cfn-resource-bridge
%define aws_path              /opt/aws
%define aws_bin_path          %{aws_path}/bin
%define aws_product_name_v    %{aws_product_name}-%{version}-%{release}
%define aws_product_path      %{aws_path}/apitools/%{aws_product_name_v}
%define aws_product_path_link %{aws_path}/apitools/%{aws_product_name}

%setup -n %{name}-%{unmangled_version}