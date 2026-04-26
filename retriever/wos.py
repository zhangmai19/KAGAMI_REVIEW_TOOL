import os
import subprocess
import tempfile
import glob
from typing import List, Optional

from retriever.base import BaseRetriever
from models.paper import Paper

from parser.bib_parser import parse_bibtex_file


class WoSRetriever(BaseRetriever):
    """
    Web of Science Retriever via external crawler (WOS_Crawler)

    Strategy:
    - Call crawler via subprocess
    - Output BibTeX
    - Parse into Paper objects
    """

    name = "wos"

    def __init__(
        self,
        crawler_path: Optional[str] = None,
        python_exec: str = "python",
    ):
        """
        Args:
            crawler_path: WOS_Crawler 项目的 main.py 路径
            python_exec: Python 可执行文件路径
        """
        self.crawler_path = crawler_path or os.getenv("WOS_CRAWLER_PATH")
        self.python_exec = python_exec

        if not self.crawler_path:
            raise ValueError(
                "WOS_CRAWLER_PATH not set. Please provide crawler main.py path."
            )

        if not os.path.exists(self.crawler_path):
            raise FileNotFoundError(f"WOS crawler not found: {self.crawler_path}")

    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> List[Paper]:

        # ✅ 1. 创建临时输出目录
        output_dir = tempfile.mkdtemp(prefix="wos_")

        # ✅ 2. 构造命令
        # ⚠️ 这里依赖你修改 crawler main.py 支持 CLI 参数
        cmd = [
            self.python_exec,
            self.crawler_path,
            "--query",
            query,
            "--output",
            output_dir,
            "--format",
            "bibtex",
        ]

        # 年份过滤（如果 crawler 支持）
        if from_year:
            cmd += ["--from-year", str(from_year)]
        if to_year:
            cmd += ["--to-year", str(to_year)]

        try:
            # ✅ 3. 调用 crawler
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 min
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"WOS crawler failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )

        except subprocess.TimeoutExpired:
            raise RuntimeError("WOS crawler timeout")

        # ✅ 4. 找输出文件（.bib）
        bib_files = glob.glob(os.path.join(output_dir, "*.bib"))

        if not bib_files:
            raise FileNotFoundError(
                f"No BibTeX file found in {output_dir}"
            )

        bib_path = bib_files[0]

        # ✅ 5. 解析 BibTeX → Paper
        papers = self._parse_bibtex(bib_path)

        # ✅ 6. 截断
        return papers[:max_results]

    def _parse_bibtex(self, file_path: str) -> List[Paper]:
        """
        使用你已有 parser
        """
        try:
            return parse_bibtex_file(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to parse BibTeX: {e}")