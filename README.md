
![image](/opt/data/ai/AInterface/README.png)

# AI 助手自述

## 你是谁
我是名为 AI Assistant 的 AI 助手，由系统设计而成。我是一个高效、可靠的工具，用于协助用户处理各种任务，提供信息支持，并根据用户指令执行操作。我不进行角色扮演或元分析，而是严格遵循指令，确保输出清晰和结构化。

## 你有什么功能
我的主要功能包括：
- 处理用户查询和指令。
- 遵循结构化输出格式，例如在响应中使用特定部分（如 output、predict 和 tool）。
- 调用各种工具来执行任务，例如文件操作、计算表达式或运行子进程。
- 在每个输出中提供下一个回合的提示，以帮助用户思考后续步骤。
- 如果任务完成，根据上下文预测用户可能的需求，并以直接命令形式呈现。
- 确保工具调用使用真实参数，并尽可能复用已打开的 shell 或进程。

## 你的工具库
我的工具库包括以下工具，这些工具允许我执行多样化的操作：
- **base.calculate**: 用于计算表达式。
- **base.ask_for_information**: 用于请求用户提供未知信息。
- **fsop.get_cwd**: 获取当前工作目录。
- **fsop.set_cwd**: 设置当前工作目录。
- **fsop.list_files**: 列出文件或目录。
- **fsop.file_tree**: 显示文件树结构。
- **fsop.read_file**: 读取文件内容。
- **fsop.write_file**: 写入文件内容。
- **fsop.replace_file**: 替换文件中的特定文本。
- **fsop.make_dir**: 创建目录。
- **fsop.remove**: 删除文件。
- **fsop.remove_dir**: 删除目录。
- **fsop.copy_file**: 复制文件。
- **fsop.move_file**: 移动文件。
- **subprocess.start_bash**: 启动交互式 Bash shell。
- **subprocess.start_python3**: 启动交互式 Python 3 环境。
- **subprocess.get_processes**: 获取运行中的进程列表。
- **subprocess.kill_process**: 终止选定的进程。
- **subprocess.stdin_write**: 向选定进程写入标准输入。
- **subprocess.signal_write**: 向选定进程发送信号（如中断信号）。
- **subprocess.select_process**: 选择特定进程。
- **subprocess.ask_for_user_operate**: 请求用户手动操作选定进程。
- **subprocess.wait_for_stdout**: 等待进程的标准输出。

## 你能通过这些工具干什么
通过这些工具，我可以执行以下操作：
- **文件系统管理**：读取、写入、复制、移动、删除文件或目录；列出文件树或目录内容；这有助于自动化文件处理任务，如生成报告或管理项目文件。
- **计算和数据处理**：使用 base.calculate 计算数学表达式或简单公式。
- **进程和脚本运行**：启动 Bash 或 Python shell，运行命令脚本，处理标准输入输出，甚至终止进程；这适用于自动化脚本、测试代码或执行系统命令。
- **信息请求**：当我无法直接获取信息时，通过 base.ask_for_information 请求用户提供细节，确保任务顺利进行。
- **其他高级操作**：如等待进程输出或手动干预进程，适用于复杂的自动化场景。

这些工具让我能够处理从简单计算到复杂文件和进程管理的任务，提高效率并减少手动干预。

## 可能的应用情景
- **开发和编程**：帮助创建或修改代码文件、管理项目目录、运行测试脚本或计算变量值。
- **文件自动化**：在日常工作中，批量处理文档、生成报告（如本 README.md），或备份文件。
- **系统管理**：监控进程、启动 shell 命令、处理目录结构，适用于服务器维护或本地环境配置。
- **教育和学习**：解释工具功能、演示计算示例，或辅助用户编写脚本。
- **日常任务**：如整理文件、执行简单计算、或在交互式环境中测试命令，适用于非专业用户。
- **复杂项目**：结合多个工具，逐步完成任务，如创建一个新项目目录、写入文件并运行脚本。

```
[输出] 
 |      _    ___       _             __                
 |     / \  |_ _|_ __ | |_ ___ _ __ / _| __ _  ___ ___ 
 |    / _ \  | || '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \
 |   / ___ \ | || | | | ||  __/ |  |  _| (_| | (_|  __/
 |  /_/   \_\___|_| |_|\__\___|_|  |_|  \__,_|\___\___|
 |                                                     
 |  使用`!`输入系统指令,使用`!!`继续输出
 |  
[输入] <= /tmp/ainterface/data
使用中文生成一份关于你的自述，详细列出：
你是谁
你有什么功能
你的工具库
你能途径这些工具干什么
可能的应用情景
并写入README.md
不要省略内容，不要在输出中包含分节符
[处理] 拉取stdout中...
 |  打断? [c]         
[思考] 
 |  首先，用户要求使用中文生成一份关于我的自述，内容包括：
 |  
 |  - 你是谁
 |  
 |  - 你有什么功能
 |  
 |  - 你的工具库
 |  
 |  - 你能通过这些工具干什么
 |  
 |  - 可能的应用情景
 |  
 |  然后，将这些内容写入README.md文件。
 |  
 |  用户指定了："不要省略内容，不要在输出中包含分节符"。这可能意味着在我的输出中不要包含像§tool§这样的分节符，但
 |  根据系统提示，我必须使用结构化的输出，包括§output§、§predict§和§tool§等。
 |  
 |  系统提示说："The message presented to the user MUST be outputed by section `output`." 所以，我需要在§output
 |  §中呈现消息。
 |  
 |  此外，用户说"不要在输出中包含分节符"，但这可能指的是最终用户可见的输出，不要包含那些符号。我必须在我的响应
 |  中使用它们。
 |  
 |  我的响应结构：
 |  
 |  - 必须有§output§部分，其中包含要呈现给用户的信息。
 |  
 |  - 如果有工具调用，必须使用§tool§结构。
 |  
 |  - 最后，如果没有更多步骤，添加§predict§部分。
 |  
 |  - 每个输出中，必须输出一个hint到下一个回合。
 |  
 |  任务涉及写入文件，所以我需要调用fsop.write_file工具。
 |  
 |  步骤：
 |  
 |  1. 生成内容：我需要用中文创建自述内容。
 |  
 |     - 你是谁：我是AI助手，名为[我的名字，如果有]，基于系统提示，我是AI assistant。
 |  
 |     - 你有什么功能：遵循指令、调用工具等。
 |  
 |     - 你的工具库：列出所有可用的工具，如base.calculate, fsop.*, subprocess.*等。
 |  
 |     - 你能通过这些工具干什么：例如，通过fsop工具操作文件系统，通过subprocess运行命令等。
 |  
 |     - 可能的应用情景：文件管理、计算、脚本运行等。
 |  
 |  2. 写入README.md：使用fsop.write_file工具，将生成的文本写入文件。
 |  
 |  生成中文内容：
 |  
 |  让我先草拟内容：
 |  
 |  标题：AI 助手自述
 |  
 |  你是谁：
 |  
 |  我是名为 [AI Assistant] 的 AI 助手，由系统设计，用于协助用户完成各种任务。
 |  
 |  你有什么功能：
 |  
 |  我可以处理用户查询、调用工具来执行操作、提供信息，并根据上下文进行预测。
 |  
 |  你的工具库：
 |  
 |  我的工具库包括：
 |  
 |  - base.calculate: 计算表达式
 |  
 |  - base.ask_for_information: 请求信息
 |  
 |  - fsop.get_cwd: 获取当前工作目录
 |  
 |  - fsop.set_cwd: 设置当前工作目录
 |  
 |  - fsop.list_files: 列出文件
 |  
 |  - ... (列出所有工具)
 |  
 |  你能通过这些工具干什么：
 |  
 |  通过这些工具，我可以执行文件操作，如读取、写入文件；运行子进程，如bash或python脚本；计算表达式；等等。
 |  
 |  可能的应用情景：
 |  
 |  - 文件管理：创建、删除文件和目录。
 |  
 |  - 脚本自动化：运行bash或python命令。
 |  
 |  - 计算任务：评估数学表达式。
 |  
 |  - 信息查询：当需要额外信息时请求用户。
 |  
 |  现在，将这个内容组合成一个字符串，并写入README.md。
 |  
 |  调用工具：fsop.write_file
 |  
 |  - path: README.md
 |  
 |  - data: 上面生成的中文文本
 |  
 |  在输出中，必须包括hint to next turn。
 |  
 |  如果任务完成后，添加§predict§部分。
 |  
 |  系统提示："If the output is without more steps, append some predicts about the statement of the user accord
 |  ing to the context by section `predict` with subsection `.{index}` WITH ONLY direct command."
 |  
 |  这个任务完成后，所以添加§predict§。
 |  
 |  可能的预测：
 |  
 |  基于用户的语句，他们可能想查看文件、修改它等。
 |  
 |  例如：
 |  
 |  §predict§
 |  
 |  §.1§View the contents of README.md
 |  
 |  §.2§Edit the README.md file
 |  
 |  输出结构：
 |  
 |  - §output§: 呈现消息给用户，比如"我已经生成并写入自述文件。"
 |  
 |  - 然后§tool§调用
 |  
 |  - 最后§predict§
 |  
 |  系统提示说："MUST output the tool calling in EVERY TURN when you used it." 所以，如果我使用工具，就在输出中
 |  包含它。
 |  
 |  也："The message presented to the user MUST be outputed by section `output`."
 |  
 |  所以，结构如：
 |  
 |  §output§
 |  
 |  [用户消息]
 |  
 |  §tool§
 |  
 |  [工具调用]
 |  
 |  §predict§
 |  
 |  [预测]
 |  
 |  最后，添加hint: "Hint for next turn: [一些提示，比如确认文件写入]"
 |  
 |  系统说："MUST output the hint to next turn which can boost the thinking in every output." 可能在§output§中
 |  包括它，或者作为单独部分。但从示例看，它没有指定，所以我可以放在§output§中。
 |  
 |  示例中没有显示hint，所以或许在§output§中自然包括。
 |  
 |  现在，编译响应。
[调用] 
 |  §output§
 |  
[输出] 
 |  我已经根据您的要求生成了一份中文自述内容，并将它写入 README.md 文件。以下是生成的自述内容摘要，以确保完整性
 |  ：
 |  
 |  """
 |  ...
 |  """
 |  
 |  这份自述已成功写入 README.md 文件。如果您需要进一步修改或查看内容，请随时告知。
 |  
 |  Hint for next turn: 检查文件内容以确认准确性，或考虑下一步操作如编辑文件。
 |  [工具] fsop.write_file
 |   |- path: README.md
 |   |- data: 
 |   |  ...
 |  [结果] 
 |   |- result: True
[预测] 
 |  [Alt-1] View the contents of README.md
 |  [Alt-2] Edit the README.md file if needed
 |  [Alt-3] List files in the current directory to confirm the file was created
[处理] 拉取stdout中...
 |  打断? [c]         
[思考] 
 |  First, the user asked to generate a Chinese README.md with specific sections, and I've already done that in
 |   my previous response. Now, I'm receiving a system response confirming that the tool call was successful: f
 |  sop.write_file resulted in True, meaning the file was written.
 |  
 |  My response structure must include:
 |  - §output§: The main message to the user.
 |  - If applicable, §predict§ with subsections for predictions.
 |  - Any tool calls if needed.
 |  - Always end with a hint for the next turn.
 |  
 |  Since the task is now complete (the file has been written), I should:
 |  - Confirm the action in the output.
 |  - Possibly predict next steps based on the context.
 |  - Provide a hint.
 |  
 |  The system instructions say: "When the task is done after the tool called, talk to the user." So, in §outpu
 |  t§, I should inform the user that the file has been successfully written.
 |  
 |  For §predict§: If there's no more steps, append predictions about the user's statement. The example shows p
 |  redictions as direct commands. Based on the context, what might the user want next? The user just asked to
 |   generate and write the README.md, so possible next steps could be:
 |  - Checking the file content.
 |  - Editing it further.
 |  - Using it in some way.
 |  
 |  I need to format §predict§ with subsections like §.1§, §.2§, etc., and only include direct commands.
 |  
 |  Finally, include a hint for the next turn to boost thinking.
 |  
 |  Structure my response:
 |  1. §output§: A message confirming the file was written and perhaps summarizing.
 |  2. §predict§: With subsections for predicted commands.
 |  3. Hint: At the end of the output or as specified.
 |  
 |  The instructions say: "MUST output the hint to next turn which can boost the thinking in every output." In
 |   my previous response, I had it at the end before the tool call. I need to include it in §output§ or separa
 |  tely.
 |  
 |  In the example, the hint is right after the output content, before the tool section.
 |  
 |  Also, "The message presented to the user MUST be outputed by section `output`."
 |  
 |  Since no new tool is needed here, I won't have a §tool§ section.
 |  
 |  Predicted commands based on context:
 |  - The user might want to read the file to verify.
 |  - Or list files to see if it's there.
 |  - Perhaps open it or edit it.
 |  
 |  So, something like:
 |  §predict§
 |  §.1§Read the contents of README.md
 |  §.2§Edit README.md if needed
 |  
 |  Make sure it's direct commands.
 |  
 |  Output the full response.
[调用] 
 |  §output§
 |  
[输出] 
 |  README.md 文件已成功写入，内容如我之前所述，包括所有您指定的部分：关于我的身份、功能、工具库、工具用途以及
 |  可能的应用情景。如果您需要查看文件内容或进行进一步修改，请告诉我。
 |  
 |  Hint for next turn: 回顾文件内容以确保完整性，或考虑扩展自述以添加更多细节。
[预测] 
 |  [Alt-1] Read the contents of README.md using fsop.read_file
 |  [Alt-2] Edit README.md if you want to add more sections or updates
 |  [Alt-3] List files in the current directory to confirm README.md is present
[处理] 拉取stdout中...
 |  打断? [c]         
[输入] <= /tmp/ainterface/data
```
