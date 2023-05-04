echo "Make sure to have a docker-compose.yml file in the same directory as this script"
echo "Make sure to have a .env file in the same directory as this script"

echo "Installing all dependencies"
pip install -r requirements.txt

echo "Checking if docker is installed"
if ! [ -x "$(command -v docker)" ]; then
  echo "Docker is not installed. Please install docker and try again"
  exit 1
fi

echo "Checking if a docker-compose.yml file exists"
if ! [ -f "docker-compose.yml" ]; then
  echo "docker-compose.yml file does not exist. Please create one and try again"
  exit 1
fi