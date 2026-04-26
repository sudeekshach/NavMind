# 🤖 NavMind: Natural Language Robot Navigation with LLMs + ROS2

NavMind is an autonomous home robot system that understands natural language instructions, navigates to target rooms, and performs systematic coverage cleaning — all narrated in real time by a local LLM.

> *"Clean the kitchen"* → Robot navigates → Covers the entire room → Returns home

---

## 🎥 Demo

*Coming soon*

---

## ✨ Features

- 🗣️ **Natural Language Control** — Type commands like *"Clean the dining room"*
- 🧠 **Local LLM Commentary** — Powered by Llama 3.2 via Ollama (no cloud required)
- 🗺️ **Autonomous Navigation** — ROS2 Nav2 stack with AMCL localization
- 🧹 **Full Room Coverage** — Systematic lawnmower pattern (like a robot vacuum)
- 📋 **Task Queue** — Queue new rooms while robot is still working
- 🏠 **6 Named Rooms** — Living room, dining room, kitchen, study, bedroom, guest room
- 🔄 **Return to Home** — Robot returns to base after every task

---

## 🏗️ System Architecture

User Input (Streamlit Chat UI)
↓
LLM Intent Parser (Ollama + Llama 3.2:1b)
↓
ROS2 Topic → /navmind/command
↓
NavMind Node (navmind_node.py)
↓
Nav2 Navigation Stack (AMCL + NavFn + DWB)
↓
TurtleBot3 Burger in Gazebo Harmonic
↓
LLM Commentary → /navmind/commentary

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Robot Simulator | Gazebo Harmonic 8.x |
| Robot Framework | ROS2 Humble |
| Navigation Stack | Nav2 (AMCL + NavFn + DWB) |
| Mapping | SLAM Toolbox |
| Robot Model | TurtleBot3 Burger |
| LLM | Llama 3.2:1b via Ollama (local) |
| Chat UI | Streamlit |
| OS | Ubuntu 22.04 (WSL2) |

---

## 📋 Prerequisites

- Ubuntu 22.04 (native or WSL2 on Windows 11)
- ROS2 Humble
- Gazebo Harmonic
- Ollama installed on host machine
- Python 3.10+

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/sudeekshach/NavMind.git
cd NavMind
```

### 2. Install ROS2 dependencies

```bash
sudo apt install -y \
  ros-humble-nav2-bringup \
  ros-humble-navigation2 \
  ros-humble-slam-toolbox \
  ros-humble-ros-gz-bridge \
  ros-humble-xacro
```

### 3. Install Python dependencies

```bash
pip3 install streamlit requests
```

### 4. Clone TurtleBot3 packages

```bash
mkdir -p ~/navmind_ws/src && cd ~/navmind_ws/src
git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3.git
git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
cd ~/navmind_ws && colcon build --symlink-install
```

### 5. Download Gazebo Fuel models

```bash
gz fuel download -u "https://fuel.gazebosim.org/1.0/OpenRobotics/models/mailbox"
gz fuel download -u "https://fuel.gazebosim.org/1.0/OpenRobotics/models/cafe table"
gz fuel download -u "https://fuel.gazebosim.org/1.0/OpenRobotics/models/first 2015 trash can"
gz fuel download -u "https://fuel.gazebosim.org/1.0/OpenRobotics/models/table marble"

# Create symlinks for spaces in model names
cd ~/.gz/fuel/fuel.gazebosim.org/openrobotics/models/
ln -s 'cafe table' cafe_table
ln -s 'first 2015 trash can' first_2015_trash_can
ln -s 'table marble' table_marble

# Create flat fuel_models directory
mkdir -p ~/navmind/fuel_models
ln -s ~/.gz/fuel/fuel.gazebosim.org/openrobotics/models/mailbox/3 ~/navmind/fuel_models/mailbox
ln -s ~/.gz/fuel/fuel.gazebosim.org/openrobotics/models/cafe_table/3 ~/navmind/fuel_models/cafe_table
ln -s ~/.gz/fuel/fuel.gazebosim.org/openrobotics/models/first_2015_trash_can/3 ~/navmind/fuel_models/first_2015_trash_can
ln -s ~/.gz/fuel/fuel.gazebosim.org/openrobotics/models/table_marble/3 ~/navmind/fuel_models/table_marble
```

### 6. Start Ollama (Windows host)

```powershell
# Windows PowerShell
$env:OLLAMA_HOST="0.0.0.0"
ollama serve

# Another PowerShell window
ollama pull llama3.2:1b
```

---

## ▶️ Running NavMind

Open 7 terminals and run each command in order:

**Terminal 1 — Gazebo Simulation**
```bash
export GZ_SIM_RESOURCE_PATH=~/navmind_ws/src/turtlebot3_simulations/turtlebot3_gazebo/models:~/navmind/fuel_models
LIBGL_ALWAYS_SOFTWARE=1 gz sim ~/NavMind/worlds/navmind_home.sdf
```
Press **▶ Play** in Gazebo.

**Terminal 2 — ROS-Gazebo Bridge**
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  --ros-args -p config_file:=$HOME/NavMind/config/ros_gz_bridge.yaml
```

**Terminal 3 — TF Fix Node**
```bash
source /opt/ros/humble/setup.bash
python3 ~/NavMind/scripts/tf_fix.py
```

**Terminal 4 — Nav2 Stack**
```bash
source /opt/ros/humble/setup.bash
source ~/navmind_ws/install/setup.bash
ros2 launch ~/NavMind/launch/navmind_home.launch.py
```

**Terminal 5 — Activate Nav2**
```bash
source /opt/ros/humble/setup.bash
bash ~/NavMind/scripts/activate_nav2.sh
```

**Terminal 6 — NavMind Node**
```bash
source /opt/ros/humble/setup.bash
python3 ~/NavMind/scripts/navmind_node.py
```

**Terminal 7 — Streamlit UI**
```bash
streamlit run ~/NavMind/dashboard/navmind_app.py
```

Open **http://localhost:8501** in your browser and start giving commands!

---

## 💬 Example Commands

| You type | What happens |
|----------|-------------|
| `Clean the kitchen` | Robot navigates to kitchen, covers it, returns home |
| `Vacuum the bedroom` | Robot navigates to bedroom, does full coverage |
| `Go clean the dining room` | Robot queues dining room task |
| `Sweep the guest room` | Robot cleans guest room systematically |

---

## 📁 Project Structure

NavMind/
├── config/
│   ├── nav2_params.yaml           # Nav2 navigation parameters
│   ├── ros_gz_bridge.yaml         # ROS↔Gazebo bridge config
│   ├── slam_toolbox_params.yaml   # SLAM mapping config
│   └── turtlebot3_burger.urdf     # Robot description
├── dashboard/
│   └── navmind_app.py             # Streamlit chat interface
├── launch/
│   └── navmind_home.launch.py     # Main ROS2 launch file
├── maps/
│   ├── house_map.pgm              # Pre-built occupancy map
│   └── house_map.yaml             # Map metadata
├── models/
│   └── turtlebot3_burger/         # Gazebo robot model
├── scripts/
│   ├── activate_nav2.sh           # Nav2 lifecycle activation
│   ├── generate_map.py            # Map generation utility
│   ├── navmind_coverage.py        # Standalone coverage script
│   ├── navmind_node.py            # Main NavMind ROS2 node
│   └── tf_fix.py                  # TF frame correction node
└── worlds/
└── navmind_home.sdf           # Gazebo house world

---

## 🔧 Troubleshooting

**AMCL not activating after launch:**
```bash
ros2 lifecycle set /amcl configure
ros2 lifecycle set /amcl activate
ros2 lifecycle set /map_server activate
```

**Ollama not reachable from WSL2:**
```bash
# Find Windows gateway IP
ip route show default | awk '{print $3}'
# Update OLLAMA_URL in scripts/navmind_node.py with this IP
```

**Robot not moving after command:**
- Check Nav2 is active: `ros2 node list | grep amcl`
- Republish initial pose: `bash scripts/activate_nav2.sh`

**Gazebo not rendering:**
- Make sure `LIBGL_ALWAYS_SOFTWARE=1` is set before launching Gazebo

---

## 🌍 Real-World Applications

- 🏠 **Smart Homes** — Autonomous room cleaning with natural language
- 🍽️ **Restaurants** — Floor cleaning between services
- 🏥 **Hospitals** — Scheduled sanitization via text commands
- 🏭 **Warehouses** — Systematic floor maintenance
- 🏢 **Offices** — After-hours autonomous cleaning

---

## 👩‍💻 Author

**Sudeeksha** — Built with ROS2, Gazebo Harmonic, Nav2, and Ollama

*[LinkedIn](https://linkedin.com/in/sudeekshach)*

---

## 📄 License

MIT License — free to use, modify, and distribute.
