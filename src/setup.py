# setup.py
import os
import glob
import shutil
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from Cython.Build import cythonize

class CustomBuildExt(build_ext):
    def run(self):
        # 1. 원래의 Cython 컴파일 수행
        super().run()
        
        # 2. 빌드가 완료된 후, 생성된 파일들의 이름에서 파이썬 접미사 제거
        # --inplace 옵션으로 인해 현재 디렉토리에 생성된 .pyd를 탐색합니다.
        for pyd_file in glob.glob("InspireRobots*.pyd"):
            # 이미 원하는 이름으로 되어있다면 패스
            if pyd_file == "InspireRobots.pyd":
                continue
            
            # 복잡한 이름을 깔끔한 이름으로 변경 (예: rh56f1_gripper.pyd)
            target_name = "InspireRobots.pyd"
            if os.path.exists(target_name):
                os.remove(target_name)
            
            shutil.move(pyd_file, target_name)
            print(f"--- [Cython] 파일 이름 변경 완료: {pyd_file} -> {target_name} ---")

# Extension의 첫 번째 인자가 최종 생성될 .pyd 파일의 이름이 됩니다.
extensions = [
    Extension(
        name="InspireRobots",  # 임의의 원하는 이름으로 지정 가능 (예: gripper_core)
        sources=["InspireRobots.py"]
    )
]

setup(
    name='rh56f1_gripper',
    # cythonize 함수 안에 빌드할 파이썬 파일명을 확장자까지 적어줍니다.
    ext_modules=cythonize(extensions, language_level="3"),
    cmdclass={'build_ext': CustomBuildExt}
)