sudo amazon-linux-extras install aws-nitro-enclaves-cli -y
sudo yum install aws-nitro-enclaves-cli-devel -y
sudo usermod -aG ne ec2-user
sudo usermod -aG docker ec2-user
sudo yum group install "development tools" -y
sudo yum install ncurses-devel ncurses -y
sudo yum install curl-devel bzip2-devel xz-devel -y

