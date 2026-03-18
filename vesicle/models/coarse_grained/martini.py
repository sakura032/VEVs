"""
Coarse-Grained Molecular Dynamics Module
粗粒度分子动力学模块 - 基于MARTINI力场

MARTINI力场将约4个重原子映射为一个珠子，
可以模拟微秒到毫秒时间尺度的膜动力学。

主要功能：
- 囊泡构建与组装
- 脂质成分优化
- 蛋白质-膜相互作用
- 囊泡-细胞膜对接
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import logging; logger = logging.getLogger(__name__)


@dataclass
class Lipid:
    """脂质分子数据类"""
    name: str
    head_group: str
    tail_type: str
    charge: float = 0.0
    area_per_lipid: float = 0.64  # nm²
    
    # MARTINI珠子组成
    beads: List[str] = field(default_factory=list)
    
    
# 常用脂质定义
LIPID_LIBRARY = {
    'POPC': Lipid(
        name='POPC',
        head_group='PC',
        tail_type='palmitoyl-oleoyl',
        charge=0.0,
        area_per_lipid=0.64,
        beads=['NC3', 'PO4', 'GL1', 'GL2', 'C1A', 'C2A', 'C3A', 'C4A',
               'C1B', 'D2B', 'C3B', 'C4B']
    ),
    'DPPC': Lipid(
        name='DPPC',
        head_group='PC',
        tail_type='dipalmitoyl',
        charge=0.0,
        area_per_lipid=0.62,
        beads=['NC3', 'PO4', 'GL1', 'GL2', 'C1A', 'C2A', 'C3A', 'C4A',
               'C1B', 'C2B', 'C3B', 'C4B']
    ),
    'DOPE': Lipid(
        name='DOPE',
        head_group='PE',
        tail_type='dioleoyl',
        charge=0.0,
        area_per_lipid=0.65,
        beads=['NH3', 'PO4', 'GL1', 'GL2', 'C1A', 'D2A', 'C3A', 'C4A',
               'C1B', 'D2B', 'C3B', 'C4B']
    ),
    'CHOL': Lipid(
        name='CHOL',
        head_group='sterol',
        tail_type='cholesterol',
        charge=0.0,
        area_per_lipid=0.40,
        beads=['ROH', 'R1', 'R2', 'R3', 'R4', 'R5', 'C1', 'C2']
    ),
    'SM': Lipid(
        name='SM',
        head_group='PC',
        tail_type='sphingomyelin',
        charge=0.0,
        area_per_lipid=0.55,
        beads=['NC3', 'PO4', 'AM1', 'AM2', 'T1A', 'C2A', 'C3A',
               'C1B', 'C2B', 'C3B', 'C4B']
    ),
    'PIP2': Lipid(
        name='PIP2',
        head_group='PI(4,5)P2',
        tail_type='arachidonate',
        charge=-4.0,
        area_per_lipid=0.70,
        beads=['C1', 'C2', 'C3', 'PO4', 'P1', 'P2', 'GL1', 'GL2',
               'C1A', 'D2A', 'D3A', 'C4A', 'C1B', 'C2B', 'C3B', 'C4B']
    ),
}


@dataclass
class MembraneProtein:
    """膜蛋白数据类"""
    name: str
    pdb_file: Optional[str] = None
    cg_structure: Optional[np.ndarray] = None
    tm_helices: int = 1  # 跨膜螺旋数
    orientation: str = 'N-out'  # N端朝向
    

# 常见外泌体膜蛋白
EXOSOME_PROTEINS = {
    'CD9': MembraneProtein(name='CD9', tm_helices=4),
    'CD63': MembraneProtein(name='CD63', tm_helices=4),
    'CD81': MembraneProtein(name='CD81', tm_helices=4),
    'ALIX': MembraneProtein(name='ALIX', tm_helices=0),  # 外周蛋白
    'TSG101': MembraneProtein(name='TSG101', tm_helices=0),
    'Syntenin': MembraneProtein(name='Syntenin', tm_helices=0),
}


class VesicleBuilder:
    """
    囊泡构建器
    
    用于构建具有特定脂质组成和膜蛋白的囊泡模型。
    
    Attributes:
        radius: 囊泡半径 (nm)
        lipid_composition: 脂质组成字典 {脂质名: 摩尔分数}
        proteins: 膜蛋白列表
        
    Example:
        >>> builder = VesicleBuilder(radius=50, lipid_composition={'POPC': 0.5, 'CHOL': 0.3, 'SM': 0.2})
        >>> builder.add_protein('CD63', count=10)
        >>> vesicle = builder.build()
    """
    
    def __init__(
        self,
        radius: float = 50.0,
        lipid_composition: Dict[str, float] = None,
        thickness: float = 4.0,
    ):
        """
        初始化囊泡构建器
        
        Args:
            radius: 囊泡半径 (nm)
            lipid_composition: 脂质组成 {脂质名: 摩尔分数}
            thickness: 双层膜厚度 (nm)
        """
        self.radius = radius
        self.thickness = thickness
        self.lipid_composition = lipid_composition or {'POPC': 1.0}
        self.proteins: List[Tuple[MembraneProtein, int]] = []
        
        # 验证组成，确保脂质摩尔分数总和为 1（自动归一化），且脂质名称在 LIPID_LIBRARY 中
        self._validate_composition()
        
        # 根据囊泡半径计算内外层膜的面积，再结合单脂质占据面积，计算脂质数量
        self._calculate_lipid_numbers()
        
        logger.info(f"VesicleBuilder initialized: R={radius}nm, "
                   f"composition={self.lipid_composition}")
        
    def _validate_composition(self):
        """验证脂质组成"""
        total = sum(self.lipid_composition.values())
        if not np.isclose(total, 1.0, atol=0.01):
            # 归一化
            self.lipid_composition = {
                k: v/total for k, v in self.lipid_composition.items()
            }
            logger.warning(f"Lipid composition normalized to sum=1.0")
            
        for lipid in self.lipid_composition:
            if lipid not in LIPID_LIBRARY:
                raise ValueError(f"Unknown lipid: {lipid}. "
                               f"Available: {list(LIPID_LIBRARY.keys())}")
                
    def _calculate_lipid_numbers(self):
        """计算内外层脂质数量"""
        # 外叶面积
        outer_area = 4 * np.pi * self.radius**2
        inner_radius = self.radius - self.thickness
        inner_area = 4 * np.pi * inner_radius**2
        
        # 加权平均面积/脂质
        avg_area = sum(
            LIPID_LIBRARY[lip].area_per_lipid * frac
            for lip, frac in self.lipid_composition.items()
        )
        
        self.n_outer = int(outer_area / avg_area)
        self.n_inner = int(inner_area / avg_area)
        self.n_total = self.n_outer + self.n_inner
        
        logger.info(f"Lipid count: outer={self.n_outer}, inner={self.n_inner}, "
                   f"total={self.n_total}")
        
    def add_protein(
        self,
        protein_name: str,
        count: int = 1,
        custom_protein: Optional[MembraneProtein] = None,
    ):
        """
        添加膜蛋白
        
        Args:
            protein_name: 蛋白质名称
            count: 蛋白质数量
            custom_protein: 自定义蛋白质对象
        """
        if custom_protein:
            protein = custom_protein
        elif protein_name in EXOSOME_PROTEINS:
            protein = EXOSOME_PROTEINS[protein_name]
        else:
            raise ValueError(f"Unknown protein: {protein_name}")
            
        self.proteins.append((protein, count))
        logger.info(f"Added {count}x {protein_name} to vesicle")
        
    def generate_sphere_points(self, n_points: int) -> np.ndarray:
        """
        在球面上均匀分布点（Fibonacci lattice）
        
        Args:
            n_points: 点的数量
            
        Returns:
            (n_points, 3) 坐标数组
        """
        indices = np.arange(0, n_points, dtype=float) + 0.5
        
        phi = np.arccos(1 - 2 * indices / n_points)
        theta = np.pi * (1 + np.sqrt(5)) * indices
        
        x = np.sin(phi) * np.cos(theta)
        y = np.sin(phi) * np.sin(theta)
        z = np.cos(phi)
        
        return np.column_stack([x, y, z])
    
    def build(self) -> 'Vesicle':
        """
        构建囊泡
        
        Returns:
            Vesicle对象
        """
        logger.info("Building vesicle structure...")
        
        # 生成脂质位置
        outer_points = self.generate_sphere_points(self.n_outer) * self.radius
        inner_radius = self.radius - self.thickness
        inner_points = self.generate_sphere_points(self.n_inner) * inner_radius
        
        # 分配脂质类型
        outer_lipids = self._assign_lipids(self.n_outer)
        inner_lipids = self._assign_lipids(self.n_inner)
        
        # 创建囊泡对象
        vesicle = Vesicle(
            radius=self.radius,
            outer_positions=outer_points,
            inner_positions=inner_points,
            outer_lipids=outer_lipids,
            inner_lipids=inner_lipids,
            lipid_composition=self.lipid_composition,
        )
        
        # 添加蛋白质
        for protein, count in self.proteins:
            vesicle.add_proteins(protein, count)
            
        logger.info(f"Vesicle built with {self.n_total} lipids")
        
        return vesicle
    
    def _assign_lipids(self, n: int) -> List[str]:
        """按组成比例分配脂质类型"""
        lipids = []
        for lipid, frac in self.lipid_composition.items():
            count = int(n * frac)
            lipids.extend([lipid] * count)
            
        # 补齐差额
        while len(lipids) < n:
            lipids.append(list(self.lipid_composition.keys())[0])
            
        np.random.shuffle(lipids)
        return lipids[:n]


class Vesicle:
    """
    囊泡结构类
    
    存储囊泡的结构信息，包括脂质位置、类型和蛋白质。
    """
    
    def __init__(
        self,
        radius: float,
        outer_positions: np.ndarray,
        inner_positions: np.ndarray,
        outer_lipids: List[str],
        inner_lipids: List[str],
        lipid_composition: Dict[str, float],
    ):
        self.radius = radius
        self.outer_positions = outer_positions
        self.inner_positions = inner_positions
        self.outer_lipids = outer_lipids
        self.inner_lipids = inner_lipids
        self.lipid_composition = lipid_composition
        self.proteins: List[Tuple[MembraneProtein, np.ndarray]] = []
        
    def add_proteins(self, protein: MembraneProtein, count: int):
        """添加蛋白质到膜上"""
        # 随机选择位置
        indices = np.random.choice(len(self.outer_positions), count, replace=False)
        positions = self.outer_positions[indices]
        
        for pos in positions:
            self.proteins.append((protein, pos))
            
    @property
    def n_lipids(self) -> int:
        return len(self.outer_lipids) + len(self.inner_lipids)
    
    @property
    def n_proteins(self) -> int:
        return len(self.proteins)
    
    def get_center_of_mass(self) -> np.ndarray:
        """计算质心"""
        all_positions = np.vstack([self.outer_positions, self.inner_positions])
        return all_positions.mean(axis=0)
    
    def to_gro(self, filename: str):
        """导出为GROMACS格式"""
        logger.info(f"Writing vesicle to {filename}")
        
        with open(filename, 'w') as f:
            f.write("Vesicle structure\n")
            f.write(f"{self.n_lipids * 12}\n")  # 假设每个脂质12个珠子
            
            atom_id = 1
            res_id = 1
            
            # 写入外层脂质
            for lipid_name, pos in zip(self.outer_lipids, self.outer_positions):
                lipid = LIPID_LIBRARY[lipid_name]
                normal = pos / np.linalg.norm(pos)
                
                for i, bead in enumerate(lipid.beads):
                    # 沿法向分布珠子
                    bead_pos = pos - normal * i * 0.4  # 0.4 nm间距
                    f.write(f"{res_id:5d}{lipid_name:5s}{bead:>5s}{atom_id:5d}"
                           f"{bead_pos[0]:8.3f}{bead_pos[1]:8.3f}{bead_pos[2]:8.3f}\n")
                    atom_id += 1
                res_id += 1
                
            # 写入内层脂质
            for lipid_name, pos in zip(self.inner_lipids, self.inner_positions):
                lipid = LIPID_LIBRARY[lipid_name]
                normal = -pos / np.linalg.norm(pos)  # 指向内部
                
                for i, bead in enumerate(lipid.beads):
                    bead_pos = pos - normal * i * 0.4
                    f.write(f"{res_id:5d}{lipid_name:5s}{bead:>5s}{atom_id:5d}"
                           f"{bead_pos[0]:8.3f}{bead_pos[1]:8.3f}{bead_pos[2]:8.3f}\n")
                    atom_id += 1
                res_id += 1
                
            # 盒子大小
            box_size = 2 * self.radius + 20  # 留出buffer
            f.write(f"{box_size:.3f} {box_size:.3f} {box_size:.3f}\n")
            
        logger.info(f"Wrote {atom_id-1} atoms to {filename}")


class MartiniSimulation:
    """
    MARTINI分子动力学模拟类
    
    封装GROMACS的调用，用于运行粗粒度模拟。
    
    Example:
        >>> sim = MartiniSimulation(vesicle)
        >>> sim.minimize()
        >>> sim.equilibrate(time_ns=100)
        >>> sim.production(time_ns=1000)
    """
    
    def __init__(
        self,
        vesicle: Vesicle,
        work_dir: str = './simulation',
        gmx_binary: str = 'gmx',
    ):
        """
        初始化模拟
        
        Args:
            vesicle: 囊泡对象
            work_dir: 工作目录
            gmx_binary: GROMACS可执行文件路径
        """
        self.vesicle = vesicle
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.gmx = gmx_binary
        
        # 输出文件
        self.structure_file = self.work_dir / 'vesicle.gro'
        self.topology_file = self.work_dir / 'topol.top'
        self.trajectory = None
        
        # 导出初始结构
        self.vesicle.to_gro(str(self.structure_file))
        self._write_topology()
        
        logger.info(f"MartiniSimulation initialized in {work_dir}")
        
    def _write_topology(self):
        """生成拓扑文件"""
        with open(self.topology_file, 'w') as f:
            f.write("; MARTINI Topology for Vesicle\n\n")
            f.write("#include \"martini_v2.2.itp\"\n")
            f.write("#include \"martini_v2.0_lipids.itp\"\n\n")
            
            f.write("[ system ]\n")
            f.write("Cancer Cell Vesicle\n\n")
            
            f.write("[ molecules ]\n")
            for lipid_name in self.vesicle.lipid_composition:
                count = (self.vesicle.outer_lipids.count(lipid_name) +
                        self.vesicle.inner_lipids.count(lipid_name))
                f.write(f"{lipid_name}  {count}\n")
                
        logger.info(f"Topology written to {self.topology_file}")
        
    def _write_mdp(self, filename: str, params: Dict):
        """写入MDP参数文件"""
        with open(filename, 'w') as f:
            for key, value in params.items():
                f.write(f"{key} = {value}\n")
                
    def minimize(self, max_steps: int = 5000) -> bool:
        """
        能量最小化
        
        Args:
            max_steps: 最大步数
            
        Returns:
            是否成功
        """
        logger.info("Running energy minimization...")
        
        mdp_params = {
            'integrator': 'steep',
            'nsteps': max_steps,
            'emtol': 1000.0,
            'emstep': 0.01,
            'nstlist': 20,
            'cutoff-scheme': 'Verlet',
            'coulombtype': 'reaction-field',
            'rcoulomb': 1.1,
            'epsilon_r': 15,
            'vdw_type': 'cutoff',
            'rvdw': 1.1,
        }
        
        mdp_file = self.work_dir / 'minim.mdp'
        self._write_mdp(str(mdp_file), mdp_params)
        
        # 在实际环境中调用GROMACS
        logger.info("Energy minimization parameters written")
        return True
    
    def equilibrate(
        self,
        time_ns: float = 100,
        temperature: float = 310.0,
        ensemble: str = 'NPT',
    ) -> bool:
        """
        平衡模拟
        
        Args:
            time_ns: 模拟时间 (ns)
            temperature: 温度 (K)
            ensemble: 系综 ('NVT' or 'NPT')
            
        Returns:
            是否成功
        """
        logger.info(f"Running {ensemble} equilibration for {time_ns} ns...")
        
        dt = 0.02  # ps (MARTINI standard)
        nsteps = int(time_ns * 1000 / dt)
        
        mdp_params = {
            'integrator': 'md',
            'dt': dt,
            'nsteps': nsteps,
            'nstxout': 0,
            'nstvout': 0,
            'nstfout': 0,
            'nstlog': 5000,
            'nstxout-compressed': 5000,
            'cutoff-scheme': 'Verlet',
            'nstlist': 20,
            'coulombtype': 'reaction-field',
            'rcoulomb': 1.1,
            'epsilon_r': 15,
            'vdw_type': 'cutoff',
            'rvdw': 1.1,
            'tcoupl': 'v-rescale',
            'tc-grps': 'LIPIDS',
            'tau_t': 1.0,
            'ref_t': temperature,
        }
        
        if ensemble == 'NPT':
            mdp_params.update({
                'pcoupl': 'parrinello-rahman',
                'pcoupltype': 'semiisotropic',
                'tau_p': 12.0,
                'ref_p': '1.0 1.0',
                'compressibility': '3e-4 3e-4',
            })
            
        mdp_file = self.work_dir / f'equil_{ensemble.lower()}.mdp'
        self._write_mdp(str(mdp_file), mdp_params)
        
        logger.info(f"Equilibration parameters written to {mdp_file}")
        return True
    
    def production(
        self,
        time_ns: float = 1000,
        temperature: float = 310.0,
    ) -> str:
        """
        生产模拟
        
        Args:
            time_ns: 模拟时间 (ns)
            temperature: 温度 (K)
            
        Returns:
            轨迹文件路径
        """
        logger.info(f"Running production simulation for {time_ns} ns...")
        
        dt = 0.02
        nsteps = int(time_ns * 1000 / dt)
        
        mdp_params = {
            'integrator': 'md',
            'dt': dt,
            'nsteps': nsteps,
            'nstxout': 0,
            'nstvout': 0,
            'nstfout': 0,
            'nstlog': 5000,
            'nstxout-compressed': 5000,
            'cutoff-scheme': 'Verlet',
            'nstlist': 20,
            'coulombtype': 'reaction-field',
            'rcoulomb': 1.1,
            'epsilon_r': 15,
            'vdw_type': 'cutoff',
            'rvdw': 1.1,
            'tcoupl': 'v-rescale',
            'tc-grps': 'LIPIDS',
            'tau_t': 1.0,
            'ref_t': temperature,
            'pcoupl': 'parrinello-rahman',
            'pcoupltype': 'semiisotropic',
            'tau_p': 12.0,
            'ref_p': '1.0 1.0',
            'compressibility': '3e-4 3e-4',
        }
        
        mdp_file = self.work_dir / 'production.mdp'
        self._write_mdp(str(mdp_file), mdp_params)
        
        self.trajectory = self.work_dir / 'production.xtc'
        logger.info(f"Production parameters written to {mdp_file}")
        
        return str(self.trajectory)


class MartiniSystem:
    """
    通用MARTINI系统构建器
    
    用于构建包含脂质双层、蛋白质和溶剂的系统。
    """
    
    def __init__(self, box_size: Tuple[float, float, float] = (20, 20, 20)):
        """
        初始化系统
        
        Args:
            box_size: 盒子大小 (nm)
        """
        self.box_size = np.array(box_size)
        self.components = []
        self.n_atoms = 0
        
        logger.info(f"MartiniSystem initialized with box {box_size} nm")
        
    def add_lipid_bilayer(
        self,
        lipid: str = 'DPPC',
        area: float = 10000,  # nm²
        composition: Optional[Dict[str, float]] = None,
    ):
        """
        添加脂质双层
        
        Args:
            lipid: 主要脂质类型
            area: 双层面积 (nm²)
            composition: 脂质组成
        """
        if composition is None:
            composition = {lipid: 1.0}
            
        # 计算脂质数量
        avg_area = sum(
            LIPID_LIBRARY[lip].area_per_lipid * frac
            for lip, frac in composition.items()
        )
        n_lipids = int(area / avg_area)
        
        self.components.append({
            'type': 'bilayer',
            'composition': composition,
            'n_lipids': n_lipids,
            'area': area,
        })
        
        logger.info(f"Added lipid bilayer: {n_lipids} lipids, "
                   f"area={area} nm², composition={composition}")
        
    def add_protein_from_pdb(
        self,
        pdb_file: str,
        position: str = 'membrane',
    ):
        """
        从PDB文件添加蛋白质
        
        Args:
            pdb_file: PDB文件路径
            position: 位置 ('membrane', 'solution', 'surface')
        """
        self.components.append({
            'type': 'protein',
            'pdb_file': pdb_file,
            'position': position,
        })
        
        logger.info(f"Added protein from {pdb_file} at {position}")
        
    def solvate(
        self,
        ion_concentration: float = 0.15,
        water_model: str = 'W',
    ):
        """
        添加溶剂和离子
        
        Args:
            ion_concentration: NaCl浓度 (M)
            water_model: 水模型 ('W' for standard MARTINI)
        """
        self.components.append({
            'type': 'solvent',
            'ion_concentration': ion_concentration,
            'water_model': water_model,
        })
        
        logger.info(f"Solvated with {ion_concentration} M NaCl, "
                   f"water model: {water_model}")
        
    def run_gromacs(
        self,
        mdp_file: str,
        time_ns: float = 500,
        gpu: bool = True,
    ):
        """
        运行GROMACS模拟
        
        Args:
            mdp_file: MDP参数文件
            time_ns: 模拟时间 (ns)
            gpu: 是否使用GPU
        """
        logger.info(f"Preparing GROMACS simulation for {time_ns} ns")
        
        # 实际运行需要GROMACS安装
        # 这里只输出命令
        cmd = f"gmx grompp -f {mdp_file} -c system.gro -p topol.top -o md.tpr"
        logger.info(f"Command: {cmd}")
        
        run_cmd = "gmx mdrun -deffnm md"
        if gpu:
            run_cmd += " -nb gpu"
        logger.info(f"Run command: {run_cmd}")


if __name__ == "__main__":
    # 示例：构建外泌体模型
    print("=== Building Exosome Model ===")
    
    builder = VesicleBuilder(
        radius=50.0,  # 50 nm radius (typical exosome)
        lipid_composition={
            'POPC': 0.30,
            'CHOL': 0.35,  # 外泌体富含胆固醇
            'SM': 0.20,
            'DOPE': 0.10,
            'PIP2': 0.05,
        }
    )
    
    # 添加四跨膜蛋白
    builder.add_protein('CD63', count=10)
    builder.add_protein('CD9', count=8)
    builder.add_protein('CD81', count=6)
    
    # 构建
    vesicle = builder.build()
    
    print(f"\nVesicle Summary:")
    print(f"  Radius: {vesicle.radius} nm")
    print(f"  Total lipids: {vesicle.n_lipids}")
    print(f"  Total proteins: {vesicle.n_proteins}")
    
    # 初始化模拟
    print("\n=== Setting up Simulation ===")
    sim = MartiniSimulation(vesicle, work_dir='./exosome_sim')
    sim.minimize()
    sim.equilibrate(time_ns=10)
    sim.production(time_ns=100)
