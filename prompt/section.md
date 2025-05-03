# Section Format Prompt

## What's the section?
The section is a way to mark the content you accessing. Via this, you can know where's the information from, and you can depend where the content will be sent to. The section is a powerful format to communicate in structured language.

## Section Format
1. Every section has a `name`, a `body` which maybe is empty, and a few of `subsection`(maybe none), of which every has its `body`.
2. To mark the beginning of a section, ALWAYS use `§section_name§`, then the body of the section without newline. Also you can use `§section_name|§` to mark a multi-line section, whose content needs next to a newline after the mark.
3. To attach a subsection to the section, ALWAYS use `§.subsection_name§`, then the body of the subsection without newline. Also you can use `§.subsection_name|§` to mark a multi-line subsection, whose content needs next to a newline after the mark.
4. Sometime you needs to mark where's the content end of this section, such as `stdin`, so you need to mark it by a newline then `§section_name:end§`.
5. Depended on the section format, NEVER write a `§` in the body of sections and subsections, or it will be parsed as a part of section structure.
6. ALWAYS be effective, so you needn't use the section format when it is not asked, such as `thinking`.


