#!/usr/bin/env python
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Font

from mtools.util.cmdlinetool import LogFileTool


class MLogExcelTool(LogFileTool):
    def __init__(self):
        """Constructor: add description to argparser."""
        LogFileTool.__init__(self, multiple_logfiles=False,
                             stdin_allowed=True)

        self.argparser.description = ('Extracts fields from log messages and '
                                      'writes them to an Excel 2010 xlsx '
                                      'file.')
        self.argparser.add_argument('--out', '-o', action='store',
                                    default=None,
                                    help=('filename to output. Default is '
                                          '<original logfile>.xlsx'))
        self.argparser.add_argument('--actual', action='store_true',
                                    help=('show the actual JSON (instead of '
                                          'patterns) for queries, sort '
                                          'keys, and planSummary.'))

    def run(self, arguments=None):
        """Copy log messages to an Excel file."""
        LogFileTool.run(self, arguments)

        # change stdin logfile name and remove the < >
        logname = self.args['logfile'].name
        if logname == '<stdin>':
            logname = 'stdin'

        if self.args['out'] is not None:
            outputname = self.args['out']
        else:
            outputname = logname + '.xlsx'

        if not os.access(os.path.dirname(os.path.realpath(outputname)),
                         os.W_OK):
            print('Cannot write to file: %s' % outputname)
            sys.exit(1)

        wb = Workbook()
        ops_ws = wb.active
        ops_ws.title = 'Operations'
        info_ws = wb.create_sheet('Information')

        ops_ws.column_dimensions['B'].width = 20
        ops_ws.column_dimensions['C'].width = 12
        ops_ws.column_dimensions['E'].width = 20
        ops_ws.column_dimensions['F'].width = 15
        ops_ws.column_dimensions['G'].width = 10
        ops_ws.column_dimensions['H'].width = 30
        ops_ws.column_dimensions['I'].width = 30
        ops_ws.column_dimensions['J'].width = 30
        ops_ws.column_dimensions['K'].width = 10
        ops_ws.column_dimensions['L'].width = 10
        ops_ws.column_dimensions['M'].width = 10
        ops_ws.column_dimensions['N'].width = 10
        ops_ws.column_dimensions['O'].width = 10

        info_ws.column_dimensions['B'].width = 20
        info_ws.column_dimensions['C'].width = 12

        ops_ws.append([
            'lineno',
            'datetime',
            'thread',
            'duration',
            'namespace',
            'command',
            'operation',
            'pattern' if not self.args['actual'] else 'query',
            'sort_pattern' if not self.args['actual'] else 'sort',
            'planSummary',
            'nscanned',
            'ntoreturn',
            'nreturned',
            'ninserted',
            'nupdated',
        ])

        info_ws.append([
            'lineno',
            'datetime',
            'thread',
            'message',
        ])
        ops_ws.freeze_panes = 'A2'
        info_ws.freeze_panes = 'A2'

        ops_row = 1

        for lineno, logevent in enumerate(self.args['logfile'], 1):
            if logevent.operation:
                # need to track the actual row number on the sheet in order to
                # apply cell format changes
                ops_row += 1

                ops_ws.append([
                    lineno,
                    logevent.datetime,
                    logevent.thread,
                    logevent.duration,
                    logevent.namespace,
                    logevent.command,
                    logevent.operation,
                    (logevent.pattern if not self.args['actual'] else
                        logevent.actual_query),
                    (logevent.sort_pattern if not self.args['actual'] else
                        logevent.actual_sort),
                    (logevent.planSummary if not self.args['actual'] else
                        logevent.actualPlanSummary),
                    logevent.nscanned,
                    logevent.ntoreturn,
                    logevent.nreturned,
                    logevent.ninserted,
                    logevent.nupdated
                ])

                # add 'ms' suffix to cell format for duration
                coord = 'D%d' % ops_row
                ops_ws[coord].number_format = '0" ms"'
            else:
                msg = logevent.line_str[logevent.line_str.index(']') + 2:]
                info_ws.append([
                    lineno,
                    logevent.datetime,
                    logevent.thread,
                    msg,
                ])

        # apply formatting to header cells
        for col in [chr(num) for num in range(ord('A'), ord('O') + 1)]:
            coord = '%s1' % col
            ops_ws[coord].font = Font(bold=True, underline='single')
        for col in [chr(num) for num in range(ord('A'), ord('D') + 1)]:
            coord = '%s1' % col
            info_ws[coord].font = Font(bold=True, underline='single')

        wb.save(outputname)


def main():
    tool = MLogExcelTool()
    tool.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
