from json import dumps, loads, JSONDecodeError
from typing import ClassVar, Union
from dataclasses import dataclass
from datetime import datetime
from copy import deepcopy

from concurrent.futures import ThreadPoolExecutor
import threading


@dataclass
class FunctionCalling:
    schemas: list[dict]
    implementations: dict

    DISABLED: ClassVar['FunctionCalling'] = None
    DEFAULT: ClassVar['FunctionCalling'] = None


class FunctionSchema(dict):
    def __init__(self, name: str, description: str, parameters: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update({
            "name": name,
            "description": description,
            "parameters": parameters
        })

    @property
    def name(self) -> str:
        return self['name']

    @name.setter
    def name(self, value: str):
        self['name'] = value

    @property
    def description(self) -> str:
        return self['description']

    @description.setter
    def description(self, value: str):
        self['description'] = value

    @property
    def parameters(self) -> dict:
        return self['parameters']


class FunctionCallResult(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.job_list = []
        self.append(dict(
            role="assistant",
            content="",
            tool_calls=self.job_list
        ))

        self.schemas: list[dict] = FunctionCalling.DEFAULT.schemas
        self.implementations: dict = FunctionCalling.DEFAULT.implementations

        self.__queue_mutex = threading.Lock()
        self.__thread_pool = ThreadPoolExecutor()
        self.__completed_jobs = 0
        self.__message_queue: list[str] = []

    def register_tools(self, schemas: list[dict], implementations: dict):
        """ Register tools with their schemas and implementations """
        if self.job_list:
            raise RuntimeError("Cannot register tools after job list has been created.")
        else:
            self.schemas = schemas
            # Keep only the implementations that are in the schemas
            names = {schema['name'] for schema in schemas}
            self.implementations = {
                name: impl for name, impl in implementations.items() if name in names
            }

    @property
    def state(self):
        with self.__queue_mutex:
            if not self.__message_queue:
                return None
            else:
                # Return the current state of the message queue
                queue = self.__message_queue
                self.__message_queue = []
                return "\n" + "\n".join(queue)

    def finalize(
        self,
        history_list: list,
        tag: tuple[str, str] = ("<tool_call>", "</tool_call>"),
        print_output: bool = False
    ) -> Union[str, False]:
        # Check if there are any pending tool calls
        with self.__queue_mutex:
            if len(self.job_list) != self.__completed_jobs:
                return False
            else:  # If no pending tool calls, finalize the result
                if len(self) < 2:  # If there is no history, return an empty string
                    return ""

                # Update the history with the current state
                if print_output:
                    print("\r"+repr(self), end="\n\n", flush=True)
                history_list.extend(deepcopy(list(self)))

                # Dump client-side tool call history
                state = ""
                if self.__message_queue:
                    state = "\n" + "\n".join(self.__message_queue)
                for data in self[1:]:
                    if 'tool_call_id' in data:
                        data['content'] = f"<cached_result:{data['tool_call_id']}>"
                result = state + "\n" + tag[0] + "\n" + dumps(dict(history=self, ensure_ascii=False)) + "\n" + tag[1]

                # Clear the job list and message queue
                self.job_list = []
                self[:] = self[:1]
                self.__completed_jobs = 0
                self.__message_queue = []
                return result

    def stage(self, calling: str, tag: tuple[str, str] = ("<tool_call>", "</tool_call>")):
        with self.__queue_mutex:
            job_id = datetime.now().strftime("call_%Y%m%d%H%M%S")
            try:
                params = loads(calling)
            except JSONDecodeError:
                pass  # TODO: Handle invalid JSON format if needed (in the future)
            name, arguments = params.get("name"), params.get("arguments")

            self.job_list.append(dict(id=job_id, function=dict(
                name=name,
                arguments=arguments
            )))
            self.__message_queue.append(tag[0] + "\n" + dumps(dict(call=dict(id=job_id, function=dict(
                name=name, arguments=deepcopy(arguments)
            ))), ensure_ascii=False) + "\n" + tag[1])

            self.__thread_pool.submit(self.do, job_id, name, arguments, tag)

    def do(
        self,
        job_id: str,
        name: str,
        arguments: dict,
        tag: tuple[str, str] = ("<tool_call>", "</tool_call>")
    ):
        # Execute the function
        try:
            if name not in self.implementations:
                raise ValueError(f"Function '{name}' is not registered.")
            result = self.implementations[name](**arguments)
        except Exception as e:
            result = str(e)

        # History and result handling
        with self.__queue_mutex:
            # Server side
            self.append(dict(role="tool", tool_call_id=job_id, content=result))

            # Client side
            self.__message_queue.append(tag[0] + "\n" + dumps(dict(result=dict(id=job_id, function=dict(
                name=name, content=f"<cached_result:{job_id}>"
            ))), ensure_ascii=False) + "\n" + tag[1])  # for immediate response

            # Increment the completed job count
            self.__completed_jobs += 1


FunctionCalling.DISABLED = FunctionCalling(schemas=[], implementations={})
FunctionCalling.DEFAULT = FunctionCalling(
    schemas=[

    ],

    implementations=dict(
    )
)
