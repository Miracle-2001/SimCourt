import os
os.environ['GRADIO_TEMP_DIR'] = './gradio_demo'
import gradio as gr
import datetime
import json
import logging
import glob  # 添加在文件开头的import部分

from rich.logging import RichHandler

date="_videos"
simplify=True #开启后，记忆共享，仅由法官总结，可以快一些 

class frontEnd:
    def __init__(self,):
        self.judge_model = ""
        self.clerk_model = ""
        self.prosecutor_model = ""
        self.defendant_model = ""
        self.advocate_model = ""
        self.speech_count = 0
        self.current_stage = 0
        # self.stages = ["准备阶段", "调查阶段", "证据阶段", "辩论阶段", "陈述阶段"]

        self.clerk_output = ""
        self.prosecutor_output = ""
        self.defendant_output = ""
        self.advocate_output = ""
        self.judge_output = ""
        self.prosecutor_box = ""
        self.defendant_box = ""
        self.clerk_box = ""
        self.judge_box = ""
        self.advocate_box = ""
        self.history_all = ""
        pass
        
    @staticmethod
    def setup_logging(log_level):
        """
        设置日志配置
        :param log_level: 日志级别
        """
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )

    @staticmethod
    def load_json(file_path):
        """
        加载JSON文件
        :param file_path: 文件路径
        :return: JSON数据
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_case_data(case_path):
        """
        加载案例数据
        :param case_path: 案例文件路径或目录路径
        :return: 包含所有案例数据的列表
        """
        cases = []
        with open(case_path, "r", encoding="utf-8") as file:
            for line in file:
                case = json.loads(line)
                cases.append(case)
        return cases
    
    def prosecutor_response(self,user_input):
        return f" {user_input}" 

    def defendant_response(self,user_input):
        return f" {user_input}" 

    def clerk_response(self,user_input):
        return f" {user_input}"  

    def judge_response(self,user_input):
        return f" {user_input}"
    
    def advocate_response(self,user_input):
        return f" {user_input}"
    # def generate_progress_bar(self):
    #     """生成进度条HTML"""
    #     progress_html = """
    #     <style>
    #     .stage-progress {
    #         display: flex;
    #         width: 100%;
    #         height: 40px;
    #         margin: 20px 0;
    #     }
    #     .stage-block {
    #         flex: 1;
    #         margin: 0 2px;
    #         display: flex;
    #         align-items: center;
    #         justify-content: center;
    #         border: 1px solid #ccc;
    #         font-size: 14px;
    #         transition: background-color 0.3s;
    #     }
    #     .stage-active {
    #         background-color: #4CAF50;
    #         color: white;
    #     }
    #     .stage-inactive {
    #         background-color: white;
    #         color: #666;
    #     }
    #     </style>
    #     <div class="stage-progress">
    #     """
        
        # for i, stage in enumerate(self.stages):
        #     active_class = "stage-active" if i == self.current_stage else "stage-inactive"
        #     progress_html += f'<div class="stage-block {active_class}">{stage}</div>'
        
        # progress_html += "</div>"
        # return progress_html
    

    # def update_stage(self, stage_index):
    #     self.current_stage = stage_index
    #     process_html = self.generate_progress_bar()
    #     return process_html
    
    # def update_stage_backend(self, stage_index):
        
    #     # self.update_stage(self, stage_index)
    #     self.current_stage = stage_index
    #     # progress = stage_index/4.0
    #     # self.progress_bar(progress=progress)

    
    def update(self,):
        # prosecutor_visible = bool(prosecutor_text)
        # defendant_visible = bool(defendant_text)
        # clerk_visible = bool(clerk_text)
        # judge_visible = bool(judge_text)
        # advocate_visible = bool(advocate_text)
        return [self.prosecutor_box, 
                self.defendant_box, 
                self.clerk_box, 
                self.judge_box, 
                self.advocate_box,
                self.history_all]
    
    def check_run(self, simulation_id):
        """
        检查是否已经运行过
        """
        dir_name = f"test_result/{date}/test_result_json"
        save_dir = f"judge_{self.judge_model}_clerk_{self.clerk_model}_prosecutor_{self.prosecutor_model}_defendant_{self.defendant_model}_advocate_{self.advocate_model}"
        simu_id = simulation_id

        # 构建完整的目录路径
        full_dir_path = f"{dir_name}/{save_dir}"
        
        # 如果目录不存在，说明肯定没有运行过
        if not os.path.exists(full_dir_path):
            print(f"目录不存在: {full_dir_path}")
            return False
        
        # 使用glob模块查找匹配的文件
        pattern = f"{full_dir_path}/case_{simu_id}_*.json"
        matching_files = glob.glob(pattern)
        
        
        return False
        # 如果找到匹配的文件，说明已经运行过
        if matching_files:
            print(f"已经运行过 {save_dir}/case_{simu_id}")
            return True
        else:
            print(f"未运行过 {save_dir}/case_{simu_id}")
            return False
    
    # 院审，启动
    def start_simluation(self, defendant_info, prosecution_statement, evidence_prosecution, evidence_defendant, judge_model, clerk_model, prosecutor_model, defendant_model, advocate_model,simulation_id=None,source=None):
        self.history_all = ""
        self.history_prosecutor = ""
        self.history_defendant = ""
        self.history_clerk = ""
        self.history_judge=""
        self.history_advocate=""
        self.speech_count = 0
        self.clear()
        
        self.judge_model = judge_model
        self.clerk_model = clerk_model
        self.prosecutor_model = prosecutor_model
        self.defendant_model = defendant_model
        self.advocate_model = advocate_model
        
        self.run_simulation(defendant_info=defendant_info, prosecution_statement=prosecution_statement, evidence_prosecution=evidence_prosecution, evidence_defendant=evidence_defendant,simulation_id=simulation_id,source=source)

    # 选择某个agent发言
    def clear(self):
        self.defendant_box=""
        self.prosecutor_box=""
        self.judge_box=""
        self.clerk_box=""
        self.advocate_box=""
        
    def agent_speak(self,role,content):
        # print(role,content)
        self.clear()
        self.speech_count += 1

        formatted_content = f'[{self.speech_count}] {content}'
    

        if role == "公诉人":
            self.prosecutor_box = formatted_content
            self.history_prosecutor += f"\n{content}"
            self.history_all += f"[{self.speech_count}] {role}: {content}\n"
        elif role == "被告人":
            self.defendant_box = formatted_content
            self.history_defendant += f"\n{content}"
            self.history_all += f"[{self.speech_count}] {role}: {content}\n"
        elif role == "书记员":
            self.clerk_box = formatted_content
            self.history_clerk += f"\n{content}"
            self.history_all += f"[{self.speech_count}] {role}: {content}\n"
        elif role=="审判长":
            self.judge_box=formatted_content
            self.history_judge+= f"\n{content}"
            self.history_all+=f"[{self.speech_count}] {role}: {content}\n"
        elif role=="辩护人":
            self.advocate_box=formatted_content
            self.history_advocate+= f"\n{content}"
            self.history_all+=f"[{self.speech_count}] {role}: {content}\n"
        else:
            raise ValueError("没有这个角色")

    # 定义存档函数
    def save_history(self,simulation_id=0):
        # 生成带有时间戳的文件名
        timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
        save_dir = f"test_result/{date}/test_result_txt/judge_{self.judge_model}_clerk_{self.clerk_model}_prosecutor_{self.prosecutor_model}_defendant_{self.defendant_model}_advocate_{self.advocate_model}"
        
        os.makedirs(save_dir, exist_ok=True)
        
        try:
            filename = f"{save_dir}/case_{simulation_id}_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.history_all)

            logging.info(f"Court session txt saved to {filename}")
            return f"本次庭审记录已保存到 {filename}"
        except Exception as e:
            return f"保存失败: {e}"
    
    
    # 创建 Gradio 界面
    def launch(self,):
        self.history_all = ""
        self.defendant_box=""
        self.prosecutor_box=""
        self.judge_box=""
        self.clerk_box=""
        self.advocate_box=""
        with gr.Blocks() as iface:   

            # self.progress_bar = gr.HTML(value=self.generate_progress_bar())
        
            gr.Markdown("<div align='center'>  <font size='70'> SimCourt </font> </div>")
            
            # 模型选择行
            gr.Markdown("## Step1 Chose the base model")
            with gr.Row():
                with gr.Column(scale=1):
                    self.judge_model = gr.Dropdown(label="Judge model", choices=["deepseek-v3-250324","claude-3-sonnet", "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"], value="deepseek-v3-250324")
                with gr.Column(scale=1):
                    self.clerk_model = gr.Dropdown(label="Stenographer model", choices=["deepseek-v3-250324","claude-3-sonnet", "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"], value="deepseek-v3-250324")
                with gr.Column(scale=1):
                    self.prosecutor_model = gr.Dropdown(label="Prosecutor model", choices=["deepseek-v3-250324", "claude-3-sonnet", "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"], value="deepseek-v3-250324")
            with gr.Row():
                with gr.Column(scale=1):
                    self.defendant_model = gr.Dropdown(label="Defendant model", choices=["deepseek-v3-250324", "claude-3-sonnet", "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"], value="deepseek-v3-250324")
                with gr.Column(scale=1):
                    self.advocate_model = gr.Dropdown(label="Attorney model", choices=["deepseek-v3-250324", "claude-3-sonnet", "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"], value="deepseek-v3-250324")

            default_defendant_information = "被告人何某，于1999年1月18日出生于云南省怒江州福贡县上坝镇，女，傈僳族，初中文化，公民身份证号码XXX，户籍地云南省怒江傈僳族自治州福贡县，现住左贡县珠冉新区红尚会所，无前科。因涉嫌危险驾驶罪于2024年5月23日被左贡县公安局取保候审。"
            default_prosecution_statement = "西藏自治区左贡县人民检察院  \n起 诉 书  \n\n左检刑诉〔2025〕54号  \n\n被告人何某，女，1999年1月18日出生，公民身份号码XXX，傈僳族，初中文化，户籍所在地云南省怒江傈僳族自治州福贡县，现住左贡县珠冉新区红尚会所，无前科。因涉嫌危险驾驶罪，于2024年5月23日被左贡县公安局取保候审，2025年3月14日经本院决定取保候审，同日由左贡县公安局执行。  \n\n本案由左贡县公安局侦查终结，以被告人何某涉嫌危险驾驶罪，于2025年3月14日移送本院审查起诉。本院受理后，同日已告知被告人有权委托辩护人和认罪认罚可能导致的法律后果，同日已告知被害人有权委托诉讼代理人，依法讯问了被告人，听取了被告人及其值班律师、被害人的意见，审查了全部案件材料。被告人同意本案适用简易程序审理。  \n\n经依法审查查明：  \n2024年5月8日3时37分，被告人何某驾驶藏B26272小型普通客车，从左贡县电信局门口往左贡县珠冉新区方向行驶，行驶至左贡县珠冉新区川渝江湖菜门口时，与周某甲停放在路边的渝BPZ220小型普通客车发生碰撞，造成车辆受损、无人员受伤的交通事故。经左贡县公安局交警大队现场检测，何某呼气式酒精检测结果为每百毫升155毫克，后经重庆市震感司法鉴定中心鉴定，其血液中酒精含量为每百毫升197毫克，且系无证驾驶。经事故认定，何某负此次事故全部责任。  \n\n案发后何某认罪认罚，如实供述犯罪事实，双方签订和解协议书，已赔偿被害人经济损失，并取得对方谅解，认定上述事实的证据如下，一、立案决定书，查获经过、取保候审决定书、道路交通事故认定书等书证，被害人周某甲的陈述，证人尼某张某的证言，被告人何某的供述和辩解，重庆震感司法鉴定中心出具的司法鉴定意见书等现场指认笔录等提取封装血液样本录音录像，现场监控视频资料。上述证据收集程序合法，内容客观真实真实，足以认定指控事实。 被告人何某对指控的犯罪事实和证据没有异议，并自愿认罪认罚。\n\n 本院认为被告人何某在道路上醉酒驾驶机动车，其行为触犯了中华人民共和国刑法第一百三十三条之一第一款第二项之规定，犯罪事实清楚，证据确实充分，应当以危险驾驶罪追究其刑事责任。被告人何某自愿认罪认罚，依据中华人民共和国刑事诉讼法第十五条的规定，可以从宽处理，根据中华人民共和国刑事诉讼法第一百七十六条的规定提起公诉，请依法判处。"
            default_evidence = [
                [
                "1.第一组书证，被告人何某的基本情况、户籍证明信、案发经过、行政立案登记表、立案决定书、立案告知书、取保候审决定书、被取保候审义务告知书、取保候审人证人资格审查表、交通公安交通管理行政强制措施凭证，公安交通管理行政处罚决定书，何某一次呼气式酒精含量检测记录表，呼吸式酒精检测结果照片，血样提取登记表，小型汽车渝BPZ220车辆信息，驾驶人员何某基本信息，公安交通管理行政处罚决定书，道路交通事故认定书，以上证据证明被告人何某案发时已满刑事责任年龄，被告人何某无刑事行政违法前科，证明案发时间为2024年5月8日0037分。案发后被告人何某归案的详细经过：被告人何某系被民公安民警查获，被动归案，归案后积极配合民警办案民警工作，无反抗逃跑行为。值班民警对何某进行三次呼吸式酒精检测，检测结果分别为每100毫升155毫克，每100毫升199毫克，每100毫升200毫克，同时有录像公章等证明了酒精检测的程序合法。此外，被告人何某醉酒驾驶的车辆，所有人是尼某，车牌型号魏派牌CC6483，何某未取得机动车驾驶证，本案的侦破程序合法。行政处罚书：被告人在未取得驾驶证情况下，驾驶机动车，已被行政处罚罚款1900元。",
                "2.第二组，言辞证据：包括证人尼某证言，张某证言，犯罪嫌疑人何某的供述与辩解，被害人周某甲的陈述。证明2024年5月8日3时37分，被告人何某驾驶藏br6272小型普通客车，从左贡县电信局门口往左贡县朱然新区方向行驶，行驶至左贡县朱然新区川渝江湖菜门口时，与周某丁停放在路边的川路边的渝BPZ220小型普通客车发生碰撞，系未造成人员受伤的交通事故。",
                "3.第三组证据，鉴定意见及视听资料，司法鉴定意见书、鉴定意见通知书、血醇检验委托书，被害人周某戊的辨认笔录、车辆指认笔录、喝酒地点、酒类指认笔录、现场指认笔录、交通事故现场图、现场监控录像、同步录音录像等证明。2024年5月8日21:00，医护人员依法提取封装何某血液同步录音录像视频。2024年5月12日，重庆市震感司法鉴定中心检测对血液样本和仪器检测过程所制的同步录音录像视频，证实现场的基本情况，以及何某的呼气式检测和酒精检测的的全过程。指认笔录证明被告人何某指认出驾驶的车辆以及碰撞的车辆及被告人何某喝酒的地点、品类等。"
                ],
                [
                "1.书证：谅解书（由被害人周某甲签署），证明被害人周某甲自愿谅解被告人何某，双方达成刑事和解",
                "2.书证：公安交通管理行政处罚决定书（由重庆市公安局交通管理局签发），证明被告人何某因无证驾驶被行政处罚罚款1900元，且已经上交。"
                ]
            ]
            # 模型选择行
            gr.Markdown("## Step2 Case Information")
            with gr.Row():  # 两列布局
                with gr.Column(): 
                    self.defendant_info = gr.Textbox(label="Defendant's Information", value = default_defendant_information, lines=5, max_lines=5)
                # with gr.Column(): 
                    self.prosecution_statement = gr.Textbox(label="Indictment", value = default_prosecution_statement, lines=5, max_lines=5)
                with gr.Column(): 
                    self.evidence_prosecution = gr.Textbox(label="Evidence proposed by Prosecutor", value = default_evidence[0], lines=5, max_lines=5)
                # with gr.Column(): 
                    self.evidence_defendant = gr.Textbox(label="Evidence proposed by Attorney", value = default_evidence[1], lines=5, max_lines=5)

            gr.Markdown("## Step3 Start the Simulation")
            self.submit_btn = gr.Button("Start Simulation!")
            
            
            with gr.Row(elem_id="courtrow", elem_classes="court_row"):
                # 背景图片容器
                with gr.Column(elem_id="courtbackground", elem_classes="court_background"):
                    gr.Image("gradio_demo/pic/court_background.jpg", 
                             label="法庭背景图", 
                             elem_id="court_image", 
                             elem_classes="court_image",
                             show_label=False)

                    # 使用 absolute 定位将文本框浮在图片上
                    self.judge_output = gr.Textbox(label="审判长", lines=2, elem_id="judge_output", 
                            elem_classes="overlay-textbox judge-textbox")
                    self.clerk_output = gr.Textbox(label="书记员", lines=2, visible=True, elem_id="clerk_output", 
                            elem_classes="overlay-textbox clerk-textbox")
                    self.prosecutor_output = gr.Textbox(
                        label="公诉人", 
                        lines=2, 
                        visible=True, 
                        elem_id="prosecutor_output", 
                        elem_classes="overlay-textbox prosecutor-textbox")
                    self.advocate_output = gr.Textbox(label="辩护人", lines=2, visible=True, elem_id="advocate_output", 
                            elem_classes="overlay-textbox advocate-textbox")
                    self.defendant_output = gr.Textbox(label="被告人", lines=2, visible=True, elem_id="defendant_output", 
                            elem_classes="overlay-textbox defendant-textbox")
                           
            self.global_output = gr.Textbox(label="全部庭审记录", lines=16, visible=True)
            # 更新进度条的函数
            def update_progress():
                return self.update_stage(self.current_stage)

            # 每个按钮的函数
            self.submit_btn.click(
                fn=self.start_simluation,
                inputs=[self.defendant_info, self.prosecution_statement, self.evidence_prosecution, self.evidence_defendant, self.judge_model, self.clerk_model, self.prosecutor_model, self.defendant_model, self.advocate_model],
                outputs=None #[prosecutor_output, defendant_output, clerk_output, judge_output, global_output]
            )
            
            # 更新进度条
            # self.update_stage_btn = gr.Button(visible=False)  # 隐藏的按钮用于触发进度条更新
            # self.update_stage_btn.click(
            #     fn=self.update_progress,
            #     inputs=[gr.Number(value=0, visible=False)],  # 隐藏的数字输入
            #     outputs=[self.progress_bar]
            # )
            # self.stage_handler = gr.State(0)
            # # 自定义CSS布局
            iface.css = """
            /* 设置背景图容器，保证图片居中显示 */
            #court_row {
                position: relative;
            }
            
            #court_background {
                position: relative;
                width: 100%;
                height: 100%;
            }
            
            #court_image {
                width: 100% !important;  /* 确保图片宽度铺满容器 */
                height: 100% !important;  /* 确保图片高度铺满容器 */
                object-fit: cover !important;  /* 保持比例并填满容器，可能会裁剪 */
                object-position: center !important;  /* 保证裁剪区域居中 */
            }
            
            .overlay-textbox {
                position: absolute;
                top: 50%;  /* 控制竖直位置 */
                left: 50%;  /* 控制水平位置 */
                max-width: 30%;
                transform: translate(-50%, -50%);  /* 精确居中 */
                background-color: rgba(255, 255, 255, 0.7);  /* 半透明背景，避免文字遮挡 */
                width: 80%;  /* 设置宽度 */
            }

            /* 审判长 */
            .judge-textbox {
                top: 45%;
                left: 50%;
                width: 50%;
            }

            /* 书记员 */
            .clerk-textbox {
                top: 20%;
                left: 85%;
                width: 40%;
            }

            /* 公诉人 */
            .prosecutor-textbox {
                top: 80%;
                left: 15%;
                width: 40%;
            }

            /* 辩护人 */
            .advocate-textbox {
                top: 80%;
                left: 85%;
                width: 40%;
            }

            /* 被告人 */
            .defendant-textbox {
                top: 90%;
                left: 50%;
                width: 40%;
            }

            .generated-content {
                color: #2196F3;  /* 蓝色表示生成内容 */
            }

            .fixed-content {
                color: #2196F3;  /* 黑色表示固定内容 */
            }
            /* 确保选择器更具体，提高优先级 */
            

            .overlay-textbox.generated-content {
                color: #2196F3 !important;  /* 蓝色表示生成内容 */
            }

            .overlay-textbox.fixed-content {
                color: #000000 !important;  /* 黑色表示固定内容 */
            }

            /* 确保 textarea 颜色应用 */
            .gradio-container .overlay-textbox.generated-content textarea {
                color: #2196F3 !important;  /* 蓝色 */
            }

            .gradio-container .overlay-textbox.fixed-content textarea {
                color: #000000 !important;  /* 黑色 */
            }
            """

            iface.load(fn=self.update,
               inputs=None, 
               outputs=[self.prosecutor_output, self.defendant_output, self.clerk_output, self.judge_output, self.advocate_output, self.global_output], 
               every=0.5)
            # iface.launch(server_name="0.0.0.0", server_port=7860)
            iface.launch(server_name="0.0.0.0", server_port=7863, share=False)
